import os
import re
import mimetypes

from core.http.response_builder import build_response, error_response, file_response

# Route Files to Handlers
from core.routes      import routes as core_routes
from items.routes     import routes as items_routes
from carts.routes     import routes as carts_routes
from deposit.routes   import routes as deposit_routes
from dashboard.routes import routes as dashboard_routes
from wishlist.routes  import routes as wishlist_routes
from messages.routes  import routes as messages_routes
from inventory.routes import routes as inventory_routes  


#Route Table

all_routes = (
    core_routes +
    items_routes +
    carts_routes +
    deposit_routes +
    dashboard_routes +
    inventory_routes +
    wishlist_routes +
    messages_routes
)



#  MIME Type Map (for static & media file serving)

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css':  'text/css',
    '.js':   'application/javascript',
    '.json': 'application/json',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif':  'image/gif',
    '.svg':  'image/svg+xml',
    '.ico':  'image/x-icon',
    '.woff': 'font/woff',
    '.woff2':'font/woff2',
    '.ttf':  'font/ttf',
    '.pdf':  'application/pdf',
}



# Path Matching Function

def match_path(pattern, actual_path):
    """
    Match a URL pattern against an actual request path and extract parameters.
    """

    # Convert pattern like /products/product_<id> into a named-group regex
        # e.g. <id>      → (?P<id>[^/]+)
        #<user_id> → (?P<user_id>[^/]+)


    regex = re.sub(r'<(\w+)>', r'(?P<\1>[^/]+)', pattern)

    regex = f'^{regex}$'  # Match the entire path

    match = re.match(regex, actual_path)

    if match:
        return True, match.groupdict()  # Return extracted parameters as a dict
    return False, {}  # No match, return empty dict for parameters



# static & media file serving

def detect_mime(file_path):
    """Return the MIME type based on file extension."""
    _, ext = os.path.splitext(file_path)
    return MIME_TYPES.get(ext.lower(), 'application/octet-stream')


def server_static_file(path):
    """
    Serve a file from the static/ directory.

    path example: '/static/css/style.css'
    Reads:        'static/css/style.css'
    """
    relative = path.lstrip('/')  # Remove leading slash
    file_path = os.path.join(os.getcwd(), relative)  # Get absolute path

    if not os.path.isfile(file_path):
        return error_response(404, f'File Not Found: {path}')
    

    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    return file_response(file_bytes, detect_mime(file_path))  


def serve_media_file(path):
    """
    Serve a file from the media/ directory (user-uploaded content).

    path example: '/media/product_images/shirt.png'
    Reads:        'media/product_images/shirt.png'
    """
    relative = path.lstrip('/')          # 'media/product_images/shirt.png'
    file_path = os.path.join(os.getcwd(), relative)

    if not os.path.isfile(file_path):
        return error_response(404, f"Media file not found: {path}")

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    return file_response(file_bytes, detect_mime(file_path))



# Main Route Function

def route(request_dict):
    """
    Match an incoming request to a handler and return response bytes.

    Steps:
        1. Extract method and path from request_dict
        2. /static/ paths  → serve_static_file()
        3. /media/  paths  → serve_media_file()
        4. Loop all_routes → find matching (method, pattern)
        5. Extract path params and inject into request_dict
        6. Call the handler
        7. No match → 404 error response

    Parameters
    ----------
    request_dict : dict
        Parsed HTTP request from http_parser.parse_request(), e.g.:
        {
            'method': 'GET',
            'path': '/products/product_42',
            'query_params': {},
            'headers': {...},
            'form_data': {},
            'cookies': {'sessionid': 'abc'},
            'path_params': {}
        }

    Returns
    -------
    bytes
        A complete HTTP response ready to send through the socket.
    """

    method = request_dict.get('method' , 'GET').upper()
    path = request_dict.get('path', '/')

    # Static Files
    if path.startswith('/static/'):
        return server_static_file(path)
    
    # Media Files
    if path.startswith('/media/'):
        return serve_media_file(path)
    

    for entry in all_routes:
        route_method, pattern, handler = entry

        if route_method != method:
            continue # Method does not match, try next route

        matched, path_params = match_path(pattern, path)

        if matched:
            # Inject extracted path params into the request dict
            # so handlers can access them via request_dict['path_params']
            request_dict['path_params'] = path_params
            return handler(request_dict)

    # 404 No route found 
    return error_response(404, f"No route found for {method} {path}")