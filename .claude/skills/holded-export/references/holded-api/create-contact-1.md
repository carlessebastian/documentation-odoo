# Create Contact

Create a new contact.

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
    "/contacts": {
      "post": {
        "operationId": "Create Contact",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "CustomId": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  },
                  "code": {
                    "type": "string"
                  },
                  "email": {
                    "type": "string"
                  },
                  "mobile": {
                    "type": "string"
                  },
                  "phone": {
                    "type": "string"
                  },
                  "type": {
                    "type": "string",
                    "description": "Options: supplier, debtor, creditor, client, lead"
                  },
                  "isperson": {
                    "type": "boolean",
                    "description": "When true the contact is created as a Contact Person instead of as a Company"
                  },
                  "iban": {
                    "type": "string"
                  },
                  "swift": {
                    "type": "string"
                  },
                  "sepaRef": {
                    "type": "string"
                  },
                  "groupId": {
                    "type": "string"
                  },
                  "taxOperation": {
                    "type": "string",
                    "description": "options for Spain (general, intra, impexp, nosujeto, receq, exento)"
                  },
                  "sepaDate": {
                    "type": "number"
                  },
                  "clientRecord": {
                    "type": "integer"
                  },
                  "supplierRecord": {
                    "type": "integer"
                  },
                  "billAddress": {
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
                      }
                    }
                  },
                  "numberingSeries": {
                    "type": "object",
                    "description": "The value of each document should be a valid ID.",
                    "properties": {
                      "invoice": {
                        "type": "string"
                      },
                      "receipt": {
                        "type": "string"
                      },
                      "salesOrder": {
                        "type": "string"
                      },
                      "purchasesOrder": {
                        "type": "string"
                      },
                      "proform": {
                        "type": "string"
                      },
                      "waybill": {
                        "type": "string"
                      }
                    }
                  },
                  "shippingAddresses": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "name": {
                          "type": "string"
                        },
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
                        "note": {
                          "type": "string"
                        },
                        "privateNote": {
                          "type": "string"
                        }
                      }
                    }
                  },
                  "defaults": {
                    "type": "object",
                    "properties": {
                      "expensesAccountRecord": {
                        "type": "integer"
                      },
                      "expensesAccountName": {
                        "type": "string"
                      },
                      "salesAccountRecord": {
                        "type": "integer"
                      },
                      "salesAccountName": {
                        "type": "string"
                      },
                      "dueDays": {
                        "type": "integer"
                      },
                      "salesTax": {
                        "type": "integer"
                      },
                      "salesTaxes": {
                        "type": "array",
                        "items": {
                          "type": "string"
                        }
                      },
                      "purchasesTax": {
                        "type": "integer"
                      },
                      "purchasesTaxes": {
                        "type": "array",
                        "items": {
                          "type": "string"
                        }
                      },
                      "accumulateInForm347": {
                        "type": "string",
                        "description": "Yes or No"
                      },
                      "paymentMethod": {
                        "type": "string",
                        "description": "Should be a valid ID"
                      },
                      "discount": {
                        "type": "integer"
                      },
                      "currency": {
                        "type": "string",
                        "description": "Currency ISO code in lowercase (e.g., eur = Euro, usd = U.S. Dollar, etc )"
                      },
                      "language": {
                        "type": "string",
                        "description": "options (es = spanish, en = english, fr = french, de = german, it = italian, ca = catalan, eu = euskera)"
                      },
                      "showTradeNameOnDocs": {
                        "type": "boolean"
                      },
                      "showCountryOnDocs": {
                        "type": "boolean"
                      }
                    }
                  },
                  "socialNetworks": {
                    "type": "object",
                    "properties": {
                      "website": {
                        "type": "string"
                      }
                    }
                  },
                  "tags": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  },
                  "note": {
                    "type": "string"
                  },
                  "contactPersons": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "name": {
                          "type": "string"
                        },
                        "phone": {
                          "type": "string"
                        },
                        "email": {
                          "type": "string"
                        }
                      }
                    },
                    "required": [
                      "name"
                    ]
                  }
                }
              }
            }
          },
          "x-examples": {
            "application/json": {
              "CustomId": "My reference",
              "name": "Custom Tech Inc.",
              "code": "B3737387",
              "email": "email@mapple.com",
              "mobile": "63738383",
              "phone": "3949494",
              "type": "supplier",
              "iban": "ES436677378638786",
              "swift": "",
              "clientRecord": 0,
              "supplierRecord": 0,
              "billAddress": {
                "address": "Carrer del Mar",
                "city": "Barcelona",
                "postalCode": 8767,
                "province": "Barcelona",
                "country": "Spain"
              },
              "defaults": {
                "salesChannel": 0,
                "expensesAccount": 0,
                "dueDays": 3,
                "paymentMethod": 0,
                "discount": 45,
                "language": "fr",
                "currency": "eur",
                "tax": "default",
                "retention": "default"
              },
              "socialNetworks": {
                "website": "www.mapple.com"
              },
              "tags": [
                "tag",
                "otherTag"
              ],
              "notes": "My note",
              "contactPersons": {
                "name": "Pep",
                "phone": "966",
                "email": "noway@frog.com"
              }
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
                      "id": "5ac4f2cec839ea004e18a463"
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "CONTACTS"
        ],
        "summary": "Create Contact",
        "description": "Create a new contact."
      }
    }
  },
  "tags": [
    {
      "name": "CONTACTS"
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