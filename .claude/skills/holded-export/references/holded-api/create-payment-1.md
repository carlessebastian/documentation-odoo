# Create Payment

Create a new payment.

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
    "/payments": {
      "post": {
        "operationId": "Create Payment",
        "summary": "Create Payment",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "bankId": {
                    "type": "string"
                  },
                  "contactId": {
                    "type": "string"
                  },
                  "amount": {
                    "type": "number"
                  },
                  "desc": {
                    "type": "string"
                  },
                  "date": {
                    "type": "integer"
                  }
                }
              }
            }
          },
          "x-examples": {
            "application/json": {
              "bankId": "5aaa82095b70640046270413",
              "contactId": "5aaa65e05b706400300ad246",
              "amount": 355,
              "desc": "Invoice F17003421",
              "date": 1520982000
            }
          }
        },
        "responses": {
          "201": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "integer"
                    },
                    "info": {
                      "type": "string"
                    },
                    "id": {
                      "type": "string"
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": {
                      "status": 1,
                      "info": "Created",
                      "id": "5ac4f2cec839ea004e18a463"
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "PAYMENTS"
        ]
      }
    }
  },
  "tags": [
    {
      "name": "PAYMENTS"
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