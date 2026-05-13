1 -  when i click to print the transaction in the report page it gives internal server error (done)

(Why this happens:
Missing Information (Incomplete Query): When you click "Print," the system fetches the transaction from the database, but it only gets the ID numbers (e.g., Buyer #5, Product #10). The print page, however, is trying to show the actual names (e.g., "John Doe," "Blue Shirt"). Since the names aren't in the data, the template engine gets confused and crashes.
Technical "Broken Links" in the Template: The print template is trying to use high-level commands like transaction.product.name or transaction.date.strftime. However, because of how the data is fetched, these objects are "Undefined" or in the wrong format. When the server tries to run these commands on non-existent data, it generates an Internal Server Error.
Profile ID Mismatch: In the "Print Deposit" section, the system is looking for your "Profile ID" in the wrong place. It's looking inside a "User" folder that doesn't contain it, which causes the database search to fail.)


2 - when i purchase an item it does not appear in the purchased items section in the inventory of my account (done)

(Why this happens:
Ownership isn't Transferred: When you buy an item, the system currently performs a "Payment Transaction"—it takes money from your balance, gives it to the seller, and records a history of the sale. However, it does not update the owner of the item or create a new entry for you in the database's inventory table.
The "Seller-Centric" Design: Right now, the items table only tracks who is selling an item. When a sale happens, it simply reduces the seller's stock (Quantity). It doesn't create a "receipt" item that belongs to you.
Inventory Page Mismatch: Your "Purchased Items" section on the inventory page is looking for items in the items table where you are listed as the owner but the item is not for sale. Since the checkout process never adds you as an "owner" of anything, this section remains empty even after a successful purchase.)



3 -  in the inventory page we added a button to add a csv file of items where it is it doesn't appear in the inventory page and also the AI description for items doesn't appear in the page to use it (done)

4 - when i click on submit review on an item in the review page it gives internal server error (done)

(The Possible Fixes:
Data Translation (Type Casting): We need to explicitly tell the server that the "Rating" is a number. Right now, it's being sent as text, and the database is being "picky" about it.
Error Handling (The safety net): We should wrap the code in a "try-except" block. This prevents the whole server from crashing if the database rejects a review. Instead, it can tell you exactly what you did wrong (e.g., "Rating must be a number").
Handling "First-Time" Reviews: If a product has never been reviewed before, the math to calculate the "Average Rating" can sometimes result in an empty value (NULL). We should add a safety rule (COALESCE) to treat an empty average as 0.0 instead of a crash.
Redirecting Instead of JSON: Instead of showing you raw code (JSON) on a white screen after you submit, the server should redirect you back to your Dashboard so you can see your updated reports.)


5 - when i click on the deposit button it gives internal server error (done)