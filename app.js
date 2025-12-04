const express = require('express');
const app = express();
const port = process.env.PORT || 8080; 

app.get('/', (req, res) => {
  // HTMLを返すのはアプリの役割
  res.send('<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>My First Web App</title></head><body><h1>Hello_World! App.js is Running!</h1></body></html>');
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});