# List Products

Get all your products.

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
      "get": {
        "operationId": "List Products",
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/product-output"
                  }
                },
                "examples": {
                  "response": {
                    "value": [
                      {
                        "id": "5abbc9980823dd002b5c36f5",
                        "kind": "simple",
                        "name": "Brand new shirt",
                        "desc": "Black shirt",
                        "typeId": "5abbc8e40823dd00274ca482",
                        "contactId": "5aaa51ab5b70640028340186",
                        "contactName": "Iron Supply",
                        "price": 95,
                        "tax": 21,
                        "total": 119.45,
                        "rates": [],
                        "hasStock": 1,
                        "stock": 2,
                        "barcode": "45the54",
                        "sku": "23454657",
                        "cost": 20,
                        "purchasePrice": 11.5,
                        "weight": 0.5,
                        "tags": [
                          "tig",
                          "tag",
                          "tug"
                        ],
                        "categoryId": "5abbc9110823dd0025411fb4",
                        "factoryCode": "32435g",
                        "attributes": [],
                        "forSale": 1,
                        "forPurchase": 1,
                        "salesChannelId": "5abbc324g3vdd002b5c36f3",
                        "expAccountId": "5abbc9980823d3245b5c36f3",
                        "warehouseId": "5abbc89e5823dd002b5c36f3",
                        "variants": [
                          {
                            "id": "5abbc9980823dd002b5c36f3",
                            "barcode": "35647",
                            "sku": "34354",
                            "price": 45,
                            "cost": 20,
                            "purchasePrice": 11.5,
                            "stock": 2
                          },
                          {
                            "id": "5abbc9980823dd002b5c36f4",
                            "barcode": "",
                            "sku": "",
                            "price": 45,
                            "cost": 20,
                            "purchasePrice": 11.5,
                            "stock": 0
                          }
                        ]
                      },
                      {
                        "id": "5abbd1cf0823dd004562b685",
                        "kind": "simple",
                        "name": "Tata shoes",
                        "desc": "brand new shoes",
                        "typeId": "480yhfn2b3498o243upj2",
                        "contactId": "2p4hjrnfob3hli2khpn",
                        "contactName": "Tata industry",
                        "price": 100,
                        "tax": 21,
                        "total": 121,
                        "rates": [],
                        "hasStock": 1,
                        "stock": 234,
                        "barcode": "232435465",
                        "sku": "234rwt54",
                        "cost": 39,
                        "purchasePrice": 11,
                        "weight": 0,
                        "tags": [
                          ""
                        ],
                        "categoryId": "5abbd15e0823dd003b085005",
                        "factoryCode": "324t5f4",
                        "attributes": [],
                        "forSale": 1,
                        "forPurchase": 1,
                        "salesChannelId": "0",
                        "expAccountId": "0",
                        "warehouseId": "0",
                        "variants": [
                          {
                            "id": "5abbd1cf0823dd004562b683",
                            "barcode": "123",
                            "sku": "123",
                            "price": 2,
                            "cost": 1,
                            "purchasePrice": 1,
                            "stock": 234
                          },
                          {
                            "id": "5abbd1cf0823dd004562b684",
                            "barcode": "",
                            "sku": "",
                            "price": 0,
                            "cost": 0,
                            "purchasePrice": 2,
                            "stock": 0
                          }
                        ]
                      },
                      {
                        "id": "5abbca020823dd00343d0a44",
                        "kind": "simple",
                        "name": "new simple product",
                        "desc": "the best simple product you can buy",
                        "typeId": "3l4kbn5j3oknl645t574354",
                        "contactId": "",
                        "contactName": "",
                        "price": 0,
                        "tax": 21,
                        "total": 0,
                        "rates": [],
                        "hasStock": 1,
                        "stock": 0,
                        "barcode": "",
                        "sku": "",
                        "cost": 0,
                        "purchasePrice": 0,
                        "weight": 0,
                        "tags": [
                          ""
                        ],
                        "categoryId": "0",
                        "factoryCode": "",
                        "attributes": [],
                        "forSale": 1,
                        "forPurchase": 1,
                        "salesChannelId": "0",
                        "expAccountId": "0",
                        "warehouseId": "0",
                        "variants": [
                          {
                            "id": "5abbca020823dd00343d0a43",
                            "barcode": "",
                            "sku": "",
                            "price": 0,
                            "cost": 0,
                            "purchasePrice": 0,
                            "stock": 0
                          }
                        ]
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "tags": [
          "PRODUCTS"
        ],
        "summary": "List Products"
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
    },
    "schemas": {
      "product-common": {
        "title": "Product Common",
        "description": "The properties that are shared amongst all versions of the Product model.",
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "kind": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "desc": {
            "type": "string"
          },
          "typeId": {
            "type": "string"
          },
          "contactId": {
            "type": "string"
          },
          "contactName": {
            "type": "string"
          },
          "price": {
            "type": "integer"
          },
          "tax": {
            "type": "integer"
          },
          "total": {
            "type": "number"
          },
          "rates": {
            "type": "array",
            "items": {
              "type": "object"
            }
          },
          "hasStock": {
            "type": "integer"
          },
          "stock": {
            "type": "integer"
          },
          "barcode": {
            "type": "string"
          },
          "sku": {
            "type": "string"
          },
          "cost": {
            "type": "integer"
          },
          "purchasePrice": {
            "type": "number"
          },
          "weight": {
            "type": "number"
          },
          "tags": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "categoryId": {
            "type": "string"
          },
          "factoryCode": {
            "type": "string"
          },
          "attributes": {
            "type": "array",
            "items": {
              "type": "object"
            }
          },
          "forSale": {
            "type": "integer"
          },
          "forPurchase": {
            "type": "integer"
          },
          "salesChannelId": {
            "type": "string"
          },
          "expAccountId": {
            "type": "string"
          },
          "warehouseId": {
            "type": "string"
          },
          "variants": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "id": {
                  "type": "string"
                },
                "barcode": {
                  "type": "string"
                },
                "sku": {
                  "type": "string"
                },
                "price": {
                  "type": "integer"
                },
                "cost": {
                  "type": "integer"
                },
                "purchasePrice": {
                  "type": "number"
                },
                "stock": {
                  "type": "integer"
                }
              }
            }
          }
        }
      },
      "product-output": {
        "title": "Product Basic Output",
        "description": "The properties that are included when fetching a list of Products.",
        "allOf": [
          {
            "type": "object",
            "properties": {}
          },
          {
            "$ref": "#/components/schemas/product-common"
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