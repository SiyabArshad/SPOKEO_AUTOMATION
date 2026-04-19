const express = require('express');
const { lookupAddressHandler } = require('./api/lookupAddress');
const { getBrowserContext } = require('./automation/browser');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Routes
app.post('/lookup-address', lookupAddressHandler);

// Initialize Browser Context on startup to ensure it's ready
app.listen(PORT, async () => {
    console.log(`Server is running on port ${PORT}`);
    
    try {
        console.log("Initializing persistent browser session...");
        await getBrowserContext();
        console.log("Browser session ready!");
    } catch (error) {
        console.error("Failed to initialize browser session:", error);
    }
});
