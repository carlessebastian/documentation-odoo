# Create Service

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
      "post": {
        "operationId": "Create Service",
        "summary": "Create Service",
        "requestBody": {
          "$ref": "#/components/requestBodies/Create_ServiceBody"
        },
        "responses": {
          "201": {
            "description": ""
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
    "requestBodies": {
      "Create_ServiceBody": {
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
                "tags": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "tax": {
                  "type": "number"
                },
                "subtotal": {
                  "type": "integer"
                },
                "salesChannelId": {
                  "type": "string"
                },
                "cost": {
                  "type": "number"
                }
              }
            }
          }
        }
      }
    },
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