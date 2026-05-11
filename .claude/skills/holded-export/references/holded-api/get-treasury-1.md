# Get Treasury Account

Get a specific treasury account.

# OpenAPI definition

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Invoice API",
    "version": "1.4",
    "description": "The Holded's Invoicing API is organized around REST, using HTTP responses code to keep you informed about what's going on. Our endpoints will returns you metada in JSON format directly from Holded."
  },
  "x-samples-languages": [
    "curl",
    "node",
    "ruby",
    "python"
  ],
  "paths": {
    "/treasury/{treasuryId}": {
      "parameters": [
        {
          "name": "treasuryId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "get": {
        "operationId": "Get Treasury",
        "summary": "Get Treasury Account",
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string"
                    },
                    "balance": {
                      "type": "integer"
                    },
                    "accountNumber": {
                      "type": "integer"
                    },
                    "iban": {
                      "type": "string"
                    },
                    "swift": {
                      "type": "string"
                    },
                    "bank": {
                      "type": "string"
                    },
                    "bankname": {
                      "type": "string"
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": {
                      "id": "5aba68b1c5d438006425ad45",
                      "name": "Abanca bank",
                      "type": "bank",
                      "balance": 0,
                      "accountNumber": 57200003,
                      "iban": "ES123456789",
                      "swift": "CAGLESMM",
                      "bank": "abanca",
                      "bankname": "Abanca"
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "TREASURIES"
        ]
      }
    }
  },
  "tags": [
    {
      "name": "TREASURIES"
    }
  ],
  "security": [
    {
      "Auth": []
    }
  ],
  "servers": [
    {
      "url": "https://api.holded.com/api/invoicing/v1"
    }
  ],
  "components": {
    "securitySchemes": {
      "Auth": {
        "type": "apiKey",
        "name": "key",
        "in": "header"
      }
    }
  },
  "x-readme": {
    "explorer-enabled": true,
    "proxy-enabled": true
  }
}
```