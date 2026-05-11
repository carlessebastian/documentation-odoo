# List Services

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
    "/services": {
      "get": {
        "operationId": "List Services",
        "summary": "List Services",
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
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
                  }
                }
              }
            }
          }
        },
        "tags": [
          "SERVICES"
        ]
      }
    }
  },
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