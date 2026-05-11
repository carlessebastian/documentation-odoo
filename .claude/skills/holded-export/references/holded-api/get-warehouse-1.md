# Get Warehouse

Get a specific warehouse.

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
    "/warehouses/{warehouseId}": {
      "parameters": [
        {
          "name": "warehouseId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "get": {
        "operationId": "Get Warehouse",
        "summary": "Get Warehouse",
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "string"
                    },
                    "userId": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "email": {
                      "type": "string"
                    },
                    "phone": {
                      "type": "string"
                    },
                    "mobile": {
                      "type": "string"
                    },
                    "address": {
                      "type": "object",
                      "properties": {
                        "address": {
                          "type": "string"
                        },
                        "city": {
                          "type": "string"
                        },
                        "postalCode": {
                          "type": "string"
                        },
                        "province": {
                          "type": "string"
                        },
                        "country": {
                          "type": "string"
                        },
                        "countryCode": {
                          "type": "string"
                        }
                      }
                    },
                    "default": {
                      "type": "boolean"
                    },
                    "warehouseRecord": {
                      "type": "integer"
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": {
                      "id": "5a05cc6e60cea100094baf2f",
                      "userId": "2344000h2o4b5s4n3o45",
                      "name": "Main Warehouse",
                      "email": "main@warehouse.com",
                      "phone": "765837638",
                      "mobile": "23456673",
                      "address": {
                        "address": "Av. Meridiana, 13",
                        "city": "Barcelona",
                        "postalCode": 3849,
                        "province": "Barcelona",
                        "country": "Spain",
                        "countryCode": "ES"
                      },
                      "default": true,
                      "warehouseRecord": 30000001
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "WAREHOUSES"
        ]
      }
    }
  },
  "tags": [
    {
      "name": "WAREHOUSES"
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