# List Payments

Get all your payments.

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
    "/payments": {
      "get": {
        "parameters": [
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
        "operationId": "List Payments",
        "summary": "List Payments",
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
                  }
                },
                "examples": {
                  "response": {
                    "value": [
                      {
                        "id": "5aaa81685b7064004342fd82",
                        "bankId": "",
                        "contactId": "",
                        "contactName": "",
                        "amount": 100,
                        "desc": "Gift",
                        "date": 1521068400
                      },
                      {
                        "id": "5aaa82455b7064004e0bbd02",
                        "bankId": "5aaa82095b70640046270413",
                        "contactId": "5aaa65e05b706400300ad246",
                        "contactName": "Benedicto",
                        "amount": 355,
                        "desc": "Invoice F17003421",
                        "date": 1520982000
                      },
                      {
                        "id": "5ab4f6f61d6d820023411433",
                        "bankId": "5aaf71763697ac000a0b34d3",
                        "contactId": "5aa939a95b70640009653d72",
                        "contactName": "Bose QC",
                        "amount": 290,
                        "desc": "Invoice F170001 ",
                        "date": 1521759600
                      }
                    ]
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