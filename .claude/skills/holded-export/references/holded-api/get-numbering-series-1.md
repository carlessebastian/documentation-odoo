# Get Numbering Series by Type

Get all your numbering series.

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
    "/numberingseries/{type}": {
      "get": {
        "operationId": "Get Numbering Series",
        "summary": "Get Numbering Series by Type",
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
                      "format": {
                        "type": "string"
                      },
                      "last": {
                        "type": "integer"
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
                        "id": "5a05cc6e60cea100094baf24",
                        "name": "Default",
                        "format": "F17%%%%",
                        "last": 6,
                        "type": "invoice"
                      },
                      {
                        "id": "5ab12cd63697ac00d1489fe3",
                        "name": "nl SO",
                        "format": "SO[YY]%%%",
                        "last": 0,
                        "type": "salesOrder"
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "tags": [
          "NUMBERING SERIES"
        ]
      },
      "parameters": [
        {
          "name": "type",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ]
    }
  },
  "tags": [
    {
      "name": "NUMBERING SERIES"
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