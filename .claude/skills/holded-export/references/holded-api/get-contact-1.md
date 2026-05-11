# Get Contact

Get a specific contact.

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
    "/contacts/{contactId}": {
      "parameters": [
        {
          "name": "contactId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "get": {
        "operationId": "Get Contact",
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
                    "customId": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "code": {
                      "type": "string"
                    },
                    "tradeName": {
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
                      "type": "string"
                    },
                    "iban": {
                      "type": "string"
                    },
                    "swift": {
                      "type": "string"
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
                          "type": "integer"
                        },
                        "province": {
                          "type": "string"
                        },
                        "country": {
                          "type": "string"
                        },
                        "countryCode": {
                          "type": "string"
                        },
                        "info": {
                          "type": "string"
                        }
                      }
                    },
                    "defaults": {
                      "type": "object",
                      "properties": {
                        "salesChannel": {
                          "type": "integer"
                        },
                        "expensesAccount": {
                          "type": "integer"
                        },
                        "dueDays": {
                          "type": "integer"
                        },
                        "paymentMethod": {
                          "type": "integer"
                        },
                        "discount": {
                          "type": "integer"
                        },
                        "language": {
                          "type": "string"
                        },
                        "currency": {
                          "type": "string"
                        },
                        "tax": {
                          "type": "string"
                        },
                        "retention": {
                          "type": "string"
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
                    "notes": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "noteId": {
                            "type": "string"
                          },
                          "name": {
                            "type": "string"
                          },
                          "description": {
                            "type": "string"
                          },
                          "color": {
                            "type": "string"
                          },
                          "updatedAt": {
                            "type": "integer"
                          },
                          "userId": {
                            "type": "string"
                          }
                        }
                      }
                    },
                    "contactPersons": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "personId": {
                            "type": "string"
                          },
                          "name": {
                            "type": "string"
                          },
                          "job": {
                            "type": "string"
                          },
                          "phone": {
                            "type": "string"
                          },
                          "email": {
                            "type": "string"
                          },
                          "sendDocumentsByDefault": {
                            "type": "boolean"
                          },
                          "linkedin": {
                            "type": "string"
                          }
                        }
                      }
                    },
                    "shippingAddresses": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "shippingId": {
                            "type": "string"
                          },
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
                            "type": "integer"
                          },
                          "province": {
                            "type": "string"
                          },
                          "country": {
                            "type": "string"
                          },
                          "countryCode": {
                            "type": "string"
                          },
                          "notes": {
                            "type": "string"
                          },
                          "privateNotes": {
                            "type": "string"
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
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": {
                      "id": "5aaa43d35b7064002613c048",
                      "customId": "myReferenceId",
                      "name": "Custom Tech Inc.",
                      "code": "B3737387",
                      "tradeName": "Mapple",
                      "email": "email@mapple.com",
                      "mobile": "63738383",
                      "phone": "3949494",
                      "type": "client",
                      "iban": "ES436677378638786",
                      "swift": "",
                      "clientRecord": 0,
                      "supplierRecord": 0,
                      "billAddress": {
                        "address": "Carrer del Mar",
                        "city": "Barcelona",
                        "postalCode": 8767,
                        "province": "Barcelona",
                        "country": "Spain",
                        "countryCode": "ES",
                        "info": "Random info"
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
                      "notes": [
                        {
                          "noteId": "5aba2365c5d43800316b2a53",
                          "name": "My first note",
                          "description": "An important note",
                          "color": "primary",
                          "updatedAt": 1522148197,
                          "userId": "5a05cc5a60cea100094baf22"
                        },
                        {
                          "noteId": "5aba26efc5d43800316b2a54",
                          "name": "Note",
                          "description": "Another note",
                          "color": "#ee575d",
                          "updatedAt": 1522149103,
                          "userId": ""
                        }
                      ],
                      "contactPersons": [
                        {
                          "personId": "5aba40fdc5d43800316b2a55",
                          "name": "Pep",
                          "job": "Ito",
                          "phone": "966",
                          "email": "noway@frog.com",
                          "sendDocumentsByDefault": true,
                          "linkedin": "no link"
                        }
                      ],
                      "shippingAddresses": [
                        {
                          "shippingId": "5aba4147c5d43800342fc4a3",
                          "name": "Mapple shipping address",
                          "address": "c/LLafranch",
                          "city": "Vilafranca del Monport ",
                          "postalCode": 899,
                          "province": "Lleida",
                          "country": "Spain",
                          "countryCode": "ES",
                          "notes": "A public note",
                          "privateNotes": "This is a private note, don't read it"
                        }
                      ],
                      "customFields": [
                        {
                          "field": "FieldOne",
                          "value": "noValue"
                        }
                      ]
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
        "summary": "Get Contact",
        "description": "Get a specific contact."
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