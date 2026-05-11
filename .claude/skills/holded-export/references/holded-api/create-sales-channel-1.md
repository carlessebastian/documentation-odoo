# Create Sales Channel

Create a new sales channel.

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
      "post": {
        "operationId": "Create Sales Channel",
        "summary": "Create Sales Channel",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": {
                    "type": "string"
                  },
                  "desc": {
                    "type": "string"
                  },
                  "accountNum": {
                    "type": "integer"
                  }
                },
                "required": [
                  "name",
                  "desc",
                  "accountNum"
                ]
              }
            }
          },
          "x-examples": {
            "application/json": {
              "name": "My brand new sales channel",
              "desc": "Main income"
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