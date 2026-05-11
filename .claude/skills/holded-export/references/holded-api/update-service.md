# Update Service

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
    "/services/{serviceId}": {
      "parameters": [
        {
          "name": "serviceId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "put": {
        "operationId": "Update Service",
        "summary": "Update Service",
        "requestBody": {
          "$ref": "#/components/requestBodies/Create_ServiceBody"
        },
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/bank-output-detailed"
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
    },
    "schemas": {
      "bank-common": {
        "title": "Bank Common",
        "description": "The properties that are shared amongst all versions of the Bank model.",
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
      "bank-output": {
        "title": "Bank Basic Output",
        "description": "The properties that are included when fetching a list of Banks.",
        "allOf": [
          {
            "type": "object",
            "properties": {}
          },
          {
            "$ref": "#/components/schemas/bank-common"
          }
        ]
      },
      "bank-output-detailed": {
        "title": "Bank Detailed Output",
        "description": "The properties that are included when fetching a single Bank.",
        "allOf": [
          {
            "$ref": "#/components/schemas/bank-output"
          },
          {
            "type": "object",
            "properties": {}
          }
        ]
      }
    }
  },
  "x-readme": {
    "explorer-enabled": true,
    "proxy-enabled": true
  }
}
```