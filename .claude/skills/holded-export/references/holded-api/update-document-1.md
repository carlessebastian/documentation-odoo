# Update Document

Update a specific document. {lotSku} field is only needed when {kind} is lots.

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
      "put": {
        "operationId": "Update Document",
        "summary": "Update Document",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "desc": {
                    "type": "string"
                  },
                  "notes": {
                    "type": "string"
                  },
                  "language": {
                    "type": "string"
                  },
                  "date": {
                    "type": "integer"
                  },
                  "paymentMethod": {
                    "type": "string"
                  },
                  "warehouseId": {
                    "type": "string",
                    "description": "Choose the warehouse for your salesorder, purchaseorder or waybill."
                  },
                  "items": {
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
                        "subtotal": {
                          "type": "integer"
                        },
                        "tax": {
                          "type": "integer"
                        },
                        "tags": {
                          "type": "array",
                          "items": {
                            "type": "string"
                          }
                        },
                        "units": {
                          "type": "integer"
                        },
                        "discount": {
                          "type": "integer"
                        },
                        "accountingAccountId": {
                          "type": "string"
                        },
                        "kind": {
                          "type": "string"
                        },
                        "sku": {
                          "type": "string"
                        },
                        "lotSku": {
                          "type": "string"
                        },
                        "supplied": {
                          "type": "string",
                          "description": "Optional (Yes/No)"
                        }
                      }
                    }
                  },
                  "salesChannelId": {
                    "type": "string"
                  },
                  "expAccountId": {
                    "type": "string"
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
                  }
                }
              }
            }
          },
          "x-examples": {
            "application/json": {
              "desc": "description goes here",
              "notes": "notes goes here",
              "language": "es",
              "date": 15243534,
              "paymentMethod": "3243546",
              "products": [
                {
                  "name": "item name",
                  "desc": "item desc",
                  "subtotal": 344,
                  "tax": 21,
                  "units": 3,
                  "discount": 0
                }
              ],
              "salesChannelId": "345463o5hj432kjb4o23n1l5j5",
              "expAccountId": "345463o5hj43n1l5jowr3onb5"
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
                      "id": "5ac4f2cec839ea004e18a463"
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
        "description": "Update a specific document. {lotSku} field is only needed when {kind} is lots."
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