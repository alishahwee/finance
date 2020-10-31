# finance

Hello! This project was created using Flask, the CS50 library, and a few other utility libraries. This website creates an imaginary environment in which users can practice buying and selling stocks with fake currency. Every new registrar starts off with $10,000 and quotes can be searched via [IEX Cloud](https://iexcloud.io/), a provider in financial data. After logging in, the user is presented with a dynamically generated portfolio page in which it will update with currently owned shares. The net total will also update as it continuously grabs updates from the API whenever the page refreshes, so the user can see how their money is doing live. Users can keep track of their entire transaction history on their history page too. Upon logging out, the user's session will clear and they will be redirected to the login page.

## What I have learned

1. Relational database management and SQLite3 implementation
2. Dotenv configuration
3. Route handling responses to GET and POST requests
4. Dynamically generated HTML pages via template engine
5. Password hashing and security
6. Error handling
