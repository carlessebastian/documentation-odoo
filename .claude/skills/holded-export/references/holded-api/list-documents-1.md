# List Documents

Get all your documents by type.

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
    "/documents/{docType}": {
      "parameters": [
        {
          "name": "docType",
          "in": "path",
          "required": true,
          "description": "docType should be one of: {invoice, salesreceipt, creditnote, salesorder, proform, waybill,estimate, purchase, purchaseorder or purchaserefund}",
          "schema": {
            "type": "string"
          }
        }
      ],
      "get": {
        "parameters": [
          {
            "name": "docType",
            "in": "path",
            "required": true,
            "description": "docType should be one of: {invoice, salesreceipt, creditnote, salesorder, proform, waybill,estimate, purchase, purchaseorder or purchaserefund}",
            "schema": {
              "type": "string"
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
          },
          {
            "name": "contactid",
            "in": "query",
            "description": "Filtering by contact Id",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "paid",
            "in": "query",
            "description": "Filtering by paid status. 0 = not paid, 1 = paid, 2 = partially paid",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "billed",
            "in": "query",
            "description": "Filtering by billed status. 0 = not billed, 1 = billed",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "sort",
            "in": "query",
            "description": "Sort documents. Options: `created-asc` to sort by creation date of documents in ascending order or `created-desc` to sort by creation date of documents in descending order",
            "schema": {
              "type": "string"
            }
          }
        ],
        "operationId": "List Documents",
        "summary": "List Documents",
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/document-output"
                  }
                },
                "examples": {
                  "response": {
                    "value": {}
                  }
                }
              },
              "new": {
                "examples": {
                  "response": {
                    "value": [
                      {
                        "id": "5ab391071d6d820034294783",
                        "contact": "5aa939a95b70640009653d72",
                        "contactName": "Mapple Inc",
                        "desc": "description goes here",
                        "date": 1521673200,
                        "dueDate": 1521673200,
                        "notes": "notes go here",
                        "products": [
                          {
                            "name": "Headphone",
                            "desc": "Best headphones you can buy",
                            "price": 299,
                            "units": 1,
                            "tax": 21,
                            "discount": 0,
                            "retention": 0,
                            "weight": 200,
                            "costPrice": 110,
                            "sku": "21324t1gv",
                            "productId": "5acccbe412d56e004903a385#5acccbe412d56e004903a384"
                          }
                        ],
                        "tax": 234.61,
                        "subtotal": 1117.18,
                        "discount": 0,
                        "total": 1351.79,
                        "language": "en",
                        "status": 2,
                        "customFields": [
                          {
                            "field": "FieldOne",
                            "value": "noValue"
                          }
                        ],
                        "docNumber": "F170001",
                        "currency": "eur",
                        "currencyChange": 1,
                        "paymentsTotal": 290,
                        "paymentsPending": 1061.79,
                        "paymentsRefunds": 0,
                        "salesChannelId": "5aba667fc5d438006425ad44"
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "tags": [
          "DOCUMENTS"
        ],
        "description": "Get all your documents by type."
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
    },
    "schemas": {
      "document-common": {
        "title": "Document Common",
        "description": "The properties that are shared amongst all versions of the Document model.",
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "contact": {
            "type": "string"
          },
          "contactName": {
            "type": "string"
          },
          "desc": {
            "type": "string"
          },
          "date": {
            "type": "integer"
          },
          "dueDate": {
            "type": "integer"
          },
          "notes": {
            "type": "string"
          },
          "products": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": {
                  "type": "string"
                },
                "desc": {
                  "type": "string"
                },
                "price": {
                  "type": "integer"
                },
                "units": {
                  "type": "integer"
                },
                "tax": {
                  "type": "integer"
                },
                "discount": {
                  "type": "integer"
                },
                "retention": {
                  "type": "integer"
                },
                "weight": {
                  "type": "integer"
                },
                "costPrice": {
                  "type": "integer"
                },
                "sku": {
                  "type": "string"
                },
                "productId": {
                  "type": "string"
                }
              }
            }
          },
          "tax": {
            "type": "number"
          },
          "subtotal": {
            "type": "number"
          },
          "discount": {
            "type": "integer"
          },
          "total": {
            "type": "number"
          },
          "language": {
            "type": "string"
          },
          "status": {
            "type": "integer"
          },
          "customFields": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "field": {
                  "type": "string"
                },
                "value": {
                  "type": "string"
                }
              }
            }
          },
          "docNumber": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "currencyChange": {
            "type": "integer"
          },
          "paymentsTotal": {
            "type": "integer"
          },
          "paymentsPending": {
            "type": "number"
          },
          "paymentsRefunds": {
            "type": "integer"
          },
          "salesChannelId": {
            "type": "string"
          }
        }
      },
      "document-output": {
        "title": "Document Basic Output",
        "description": "The properties that are included when fetching a list of Documents.",
        "allOf": [
          {
            "type": "object",
            "properties": {}
          },
          {
            "$ref": "#/components/schemas/document-common"
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