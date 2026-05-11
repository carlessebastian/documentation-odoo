# Create Document

Create a new document type.

> ❗️ Matching products or services
>
> To match products or services you have already created inside Holded, you can use the "sku" field for products, or the "serviceId" field for services.

> ❗️ Purchase notes / Purchases receipts
>
> If you want to create a purchase receipt, you will need to set the **docType** as **purchase** and add this field in your JSON:
>
> * **"isReceipt": true**

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
      "post": {
        "operationId": "Create Document",
        "summary": "Create Document",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "applyContactDefaults": {
                    "type": "boolean",
                    "description": "Contact defaults are applied by default. If you don't want to apply it, set this field to false"
                  },
                  "contactCode": {
                    "type": "string",
                    "description": "(NIF / CIF / VAT) Field required if you want to choose an existing contact and contactId field is empty"
                  },
                  "contactId": {
                    "type": "string",
                    "description": "(Contact ID) Field required if you want to choose an existing contact and contactCode field is empty"
                  },
                  "contactName": {
                    "type": "string",
                    "description": "Field required if contactCode and contactId fields are empty and you want to create a new contact"
                  },
                  "contactEmail": {
                    "type": "string"
                  },
                  "contactAddress": {
                    "type": "string"
                  },
                  "contactCity": {
                    "type": "string"
                  },
                  "contactCp": {
                    "type": "string"
                  },
                  "contactProvince": {
                    "type": "string"
                  },
                  "contactCountryCode": {
                    "type": "string"
                  },
                  "desc": {
                    "type": "string"
                  },
                  "date": {
                    "type": "integer"
                  },
                  "notes": {
                    "type": "string"
                  },
                  "salesChannelId": {
                    "type": "string",
                    "description": "Set an existing account id"
                  },
                  "paymentMethodId": {
                    "type": "string"
                  },
                  "designId": {
                    "type": "string"
                  },
                  "language": {
                    "type": "string"
                  },
                  "warehouseId": {
                    "type": "string",
                    "description": "Choose the warehouse for your salesorder, purchaseorder or waybill."
                  },
                  "approveDoc": {
                    "type": "boolean",
                    "description": "Choose if the document needs to be approved or not. The default option is False."
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
                        "units": {
                          "type": "number"
                        },
                        "sku": {
                          "type": "string"
                        },
                        "serviceId": {
                          "type": "string"
                        },
                        "accountingAccountId": {
                          "type": "string"
                        },
                        "subtotal": {
                          "type": "number"
                        },
                        "discount": {
                          "type": "number"
                        },
                        "tax": {
                          "type": "integer",
                          "description": "IVA percentage. In case you need to inform more than one tax, use the field taxes instead"
                        },
                        "taxes": {
                          "type": "array",
                          "description": "Comma separated Tax keys. e.g. (s_iva_21,s_ret_19)",
                          "items": {
                            "type": "string"
                          }
                        },
                        "supplied": {
                          "type": "string",
                          "description": "Optional (Yes/No)"
                        },
                        "tags": {
                          "type": "array",
                          "items": {
                            "type": "string"
                          }
                        }
                      }
                    }
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
                  "invoiceNum": {
                    "type": "string"
                  },
                  "numSerieId": {
                    "type": "string"
                  },
                  "currency": {
                    "type": "string"
                  },
                  "currencyChange": {
                    "type": "number"
                  },
                  "tags": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  },
                  "dueDate": {
                    "type": "integer"
                  },
                  "shippingAddress": {
                    "type": "string"
                  },
                  "shippingPostalCode": {
                    "type": "string"
                  },
                  "shippingCity": {
                    "type": "string"
                  },
                  "shippingProvince": {
                    "type": "string"
                  },
                  "shippingCountry": {
                    "type": "string"
                  },
                  "salesChannel": {
                    "type": "number"
                  },
                  "directDebitProvider": {
                    "type": "string",
                    "description": "When specified, triggers automatic payment collection via the given direct debit provider. Requires a valid paymentMethodId matching an active connection for that provider, and the invoice contact must have an active mandate.",
                    "example": "gocardless"
                  }
                },
                "required": [
                  "date"
                ]
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
                  "$ref": "#/components/schemas/document-output-detailed"
                },
                "examples": {
                  "response": {
                    "value": {
                      "status": 1,
                      "id": "5acce41e12d56e005e0e62d3",
                      "invoiceNum": "F170009",
                      "contactId": "5ac3a7b68fbd9d000f07e237"
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
        "description": "Create a new document type."
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
      },
      "document-output-detailed": {
        "title": "Document Detailed Output",
        "description": "The properties that are included when fetching a single Document.",
        "allOf": [
          {
            "$ref": "#/components/schemas/document-output"
          },
          {
            "type": "object",
            "properties": {}
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