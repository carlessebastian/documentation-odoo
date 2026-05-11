# List all your entries

List all the entries you have in your daily ledger.

# OpenAPI definition

```json
{
  "openapi": "3.0.0",
  "info": {
    "description": "The Holded's Accounting API is organized around REST, using HTTP responses code to keep you informed about what's going on. Our endpoints will returns you metada in JSON format directly from Holded.",
    "version": "1.0.0",
    "title": "Accounting API",
    "contact": {
      "email": "developers@holded.com"
    }
  },
  "x-samples-languages": [
    "curl",
    "node",
    "ruby",
    "python"
  ],
  "security": [
    {
      "Auth": []
    }
  ],
  "tags": [
    {
      "name": "Daily Ledger",
      "description": "CRUD Daily Ledger"
    }
  ],
  "paths": {
    "/dailyledger": {
      "get": {
        "tags": [
          "Daily Ledger"
        ],
        "summary": "List all your entries",
        "operationId": "listDailyLedger",
        "description": "List all the entries you have in your daily ledger.\n",
        "parameters": [
          {
            "in": "query",
            "name": "page",
            "description": "the response is paginated and limited to 500 entries,",
            "required": false,
            "schema": {
              "type": "number"
            }
          },
          {
            "name": "starttmp",
            "in": "query",
            "description": "Starting timestamp",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "endtmp",
            "in": "query",
            "description": "Ending timestamp",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "search results matching criteria"
          },
          "400": {
            "description": "bad input parameter"
          }
        }
      }
    }
  },
  "servers": [
    {
      "url": "https://api.holded.com/api/accounting/v1"
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