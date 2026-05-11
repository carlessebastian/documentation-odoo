# Create Product

Create a new product.

> ❗️ Products creation
>
> If you don't have the Inventory app, the only kind of products you are allowed to create is simple ("kind":"simple").\
> If you are enjoying our Inventory app, your are allowed to create different types of products such as "lots, variants or pack".

> 📘 If you have the Inventory app..
>
> In order to create a product with variants, lots or pack you just have to set the field kind to your desired type. Then you can add a variants array field (in the pack case, instead of "variants" the name of the field should be "packItems") with the following objects structure as follow:

```json
{
  "kind": "variants",
  "variants": [
    {
      "code":"0123i",
      "sku":"sku1",
      "subtotal":20,
      "cost": 5,
      "purchasePrice": 4,
      "stock": 10
    }
  ]
}

{
  "kind": "lots",
  "variants": [
    {
			"code":"3333test",
      "sku":"ps123",
      "desc":"my first lot",
      "creationDate": 1540887390,
      "endDate": 1546166520
    }
  ]
}

{
  "kind": "pack",
  "packItems": [
    {
      "productId":"5bc45f5b4c4bea00183e8096",
      "variantId":"5bc45f5b4c4bea00183e8095",
      "units": 100
    }
  ]
}
```

##

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
    "/products": {
      "post": {
        "operationId": "Create Product",
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
                  "price": {
                    "type": "number"
                  },
                  "tax": {
                    "type": "number"
                  },
                  "cost": {
                    "type": "number"
                  },
                  "calculatecost": {
                    "type": "number"
                  },
                  "purchasePrice": {
                    "type": "number"
                  },
                  "tags": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  },
                  "barcode": {
                    "type": "string"
                  },
                  "sku": {
                    "type": "string"
                  },
                  "weight": {
                    "type": "number"
                  },
                  "stock": {
                    "type": "integer"
                  }
                }
              }
            }
          },
          "x-examples": {
            "application/json": {},
            "new": {
              "kind": "simple",
              "name": "Brand new shirt"
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
        "summary": "Create Product"
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