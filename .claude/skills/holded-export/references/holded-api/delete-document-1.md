# Delete Document

Delete specific document type.

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
    "/documents/{docType}/{documentId}": {
      "parameters": [
        {
          "name": "docType",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        },
        {
          "name": "documentId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "delete": {
        "operationId": "Delete Document",
        "summary": "Delete Document",
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "examples": {
                  "response": {
                    "value": {
                      "status": 1,
                      "info": "Successfully deleted",
                      "id": "5aba68b1c5d438006425ad45"
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "DOCUMENTS"
        ],
        "description": "Delete specific document type."
      }
    }
  },
  "tags": [
    {
      "name": "DOCUMENTS"
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