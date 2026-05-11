# Update Product

Update a specific product.

Only the params included in the operation will update the product.

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
    "/products/{productId}": {
      "parameters": [
        {
          "name": "productId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "put": {
        "operationId": "Update Product",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "kind": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  },
                  "desc": {
                    "type": "string"
                  },
                  "tax": {
                    "type": "integer"
                  },
                  "subtotal": {
                    "type": "number"
                  },
                  "barcode": {
                    "type": "string"
                  },
                  "sku": {
                    "type": "string"
                  },
                  "cost": {
                    "type": "number"
                  },
                  "purchasePrice": {
                    "type": "number"
                  },
                  "weight": {
                    "type": "number"
                  }
                }
              }
            }
          },
          "x-examples": {
            "application/json": {
              "kind": "simple",
              "name": "Brand new shirt",
              "desc": "Black shirt",
              "tax": 21,
              "subtotal": 119.45,
              "barcode": "45the54",
              "sku": "23454657",
              "cost": 20,
              "purchasePrice": 10,
              "weight": 0.5
            }
          }
        },
        "responses": {
          "200": {
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
                      "info": "Updated",
                      "id": "5aa97e595b706400153f9f94"
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "PRODUCTS"
        ],
        "summary": "Update Product"
      }
    }
  },
  "tags": [
    {
      "name": "PRODUCTS"
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