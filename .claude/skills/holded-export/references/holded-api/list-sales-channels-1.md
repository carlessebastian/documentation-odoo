# List Sales Channels

Get all your sales channels.

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
    "/saleschannels": {
      "get": {
        "operationId": "List Sales Channels",
        "summary": "List Sales Channels",
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
                      "desc": {
                        "type": "string"
                      },
                      "color": {
                        "type": "string"
                      },
                      "accNum": {
                        "type": "integer"
                      }
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": [
                      {
                        "id": "5aba667fc5d438006425ad44",
                        "name": "My brand new sales channel",
                        "desc": "Main income",
                        "color": "#507C6C",
                        "accNum": 700002
                      },
                      {
                        "id": "5aba667fc5d438006425ad44",
                        "name": "My second brand new channel",
                        "desc": "Second income stream",
                        "color": "#507C6C",
                        "accNum": null
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "tags": [
          "SALES CHANNELS"
        ]
      }
    }
  },
  "tags": [
    {
      "name": "SALES CHANNELS"
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