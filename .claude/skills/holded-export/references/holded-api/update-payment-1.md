# Update Payment

Update a specific payment.

Only the params included in the operation will update the payment.

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
      "put": {
        "operationId": "Update Payment",
        "summary": "Update Payment",
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
                    "type": "integer"
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
              "bankId": "5aaf71763697ac000a0b34d3",
              "contactId": "5aa939a95b70640009653d72",
              "amount": 290,
              "desc": "Invoice F170001 ",
              "date": 1521759600
            }
          }
        },
        "responses": {
          "200": {
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
                      "info": "Updated",
                      "id": "5aba68b1c5d438006425ad45"
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