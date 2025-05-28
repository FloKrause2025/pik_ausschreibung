## What is this PY Code about? ##

In this python script, we have done the following things:

1. Extraction all necessary informations from a PDF-file (up to 200 pages long)
2. Modifying Product describtion for a good search query
3. Searching the web for that specific Search query
4. Getting the Top 3 results URL's
5. Scraping all 3 URL's and extraction important informations as of Brand, Product description & Price

After we run through the PDF once, we iterate again and do the followng:

1. Checking which brand was find the most
2. Do another Websearch with the "Brand" as a modifier to get additional products from that brand

After all entries are done:

1. Adding to each Product a category
2. Adding all Products into Database
3. Adding a search functionality for the database, to check the next PDF's if certain products has been scraped already

## How to trigger that script

We have build a simple Web-App where the user can upload and send the file to the python script. In return it will get a complete finished EXCEL-Sheet with all entries.
