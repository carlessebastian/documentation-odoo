# Get Taxes

Get all the taxes information for a specific account

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
    "/taxes": {
      "get": {
        "operationId": "getTaxes",
        "summary": "Get Taxes",
        "description": "Get all the taxes information for a specific account",
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
                      "name": {
                        "type": "string"
                      },
                      "amount": {
                        "type": "string"
                      },
                      "scope": {
                        "type": "string"
                      },
                      "key": {
                        "type": "string"
                      },
                      "group": {
                        "type": "string"
                      },
                      "type": {
                        "type": "string"
                      }
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": [
                      {
                        "name": "IVA 21%",
                        "amount": "21",
                        "scope": "sales",
                        "key": "s_iva_21",
                        "group": "iva",
                        "type": "percentage"
                      },
                      {
                        "name": "IVA 10%",
                        "amount": "10",
                        "scope": "sales",
                        "key": "s_iva_10",
                        "group": "iva",
                        "type": "percentage"
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "tags": [
          "TAXES"
        ]
      }
    }
  },
  "tags": [
    {
      "name": "TAXES"
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