# List Warehouses

Get all your warehouses.

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
    "/warehouses": {
      "get": {
        "operationId": "List Warehouses",
        "summary": "List Warehouses",
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
                  }
                },
                "examples": {
                  "response": {
                    "value": [
                      {
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
                      },
                      {
                        "id": "5aab9ae87bdcef002641e0c3",
                        "userId": "5a05cc5a60cea100094baf22",
                        "name": "Second warehouse",
                        "email": "second@warehouse.com",
                        "phone": "",
                        "mobile": "",
                        "address": {
                          "address": "Main Street, 3",
                          "city": "London",
                          "postalCode": "04747",
                          "province": "London",
                          "country": "United Kingdom",
                          "countryCode": "UK"
                        },
                        "default": false,
                        "warehouseRecord": null
                      },
                      {
                        "id": "5aaba5237bdcef002c4979d5",
                        "userId": "",
                        "name": "Third warehouse",
                        "email": "third@warehouse.com",
                        "phone": "123",
                        "mobile": "123",
                        "address": {
                          "address": "Av. Blasco Ibañez, 34",
                          "city": "Valencia",
                          "postalCode": 8054,
                          "province": "Valencia",
                          "country": "Spain",
                          "countryCode": "ES"
                        },
                        "default": false,
                        "warehouseRecord": null
                      }
                    ]
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