// server.js の例
const express = require('express');
const app = express();

// Azure App Serviceは環境変数PORTを設定します
const port = process.env.PORT || 8080; 

app.get('/', (req, res) => {
  res.send('<h1>Node.js App Service is Running!</h1>');
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});