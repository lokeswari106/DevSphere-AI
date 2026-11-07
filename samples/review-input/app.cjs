// Intentionally vulnerable classroom REVIEW fixture. Never deploy or execute this server.
const express = require('express');
const fs = require('node:fs');
const app = express();
app.use(express.json());
app.get('/calculate', (req, res) => {
  const value = eval(req.query.expression); // untrusted dynamic evaluation
  res.json({ value });
});
app.get('/files', (req, res) => {
  res.send(fs.readFileSync('/srv/uploads/' + req.query.name, 'utf8'));
});
app.get('/users/:id', (req, res) => {
  // No authentication or per-user authorization.
  res.json({ id: req.params.id, email: 'classroom-fixture@example.com' });
});
module.exports = app;
