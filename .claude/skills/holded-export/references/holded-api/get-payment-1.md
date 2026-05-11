# Get Payment

Get a specific payment.

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
    "/payments/{paymentId}": {
      "parameters": [
        {
          "name": "paymentId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "get": {
        "operationId": "Get Payment",
        "summary": "Get Payment",
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
                    "bankId": {
                      "type": "string"
                    },
                    "contactId": {
                      "type": "string"
                    },
                    "contactName": {
                      "type": "string"
                    },
                    "amount": {
                      "type": "integer"
                    },
                    "desc": {
                      "type": "string"
                    },
                    "date": {
                      "type": "integer"
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": {
                      "id": "5ab4f6f61d6d820023411433",
                      "bankId": "5aaf71763697ac000a0b34d3",
                      "contactId": "5aa939a95b70640009653d72",
                      "contactName": "Bose QC",
                      "amount": 290,
                      "desc": "Invoice F170001 ",
                      "date": 1521759600
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