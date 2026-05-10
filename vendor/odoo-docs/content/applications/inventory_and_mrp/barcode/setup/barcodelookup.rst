:show-content:

==============
Barcode Lookup
==============

`Barcode Lookup <https://www.barcodelookup.com/>`_ allows for the scanning of products' barcodes
(:abbr:`UPC (Universal Product Code)`, :abbr:`EAN (European Article Number)`, or :abbr:`ISBN
(International Standard Book Number)`) to automatically create them as products in an Odoo database,
complete with product names, descriptions, images, categories, etc.

.. _barcodelookup/configuration:

Configuration
-------------

To use Barcode Lookup, an API key is required. Visit the `API page
<https://www.barcodelookup.com/api#sign-up>`_ on the Barcode Lookup website and choose an
appropriate plan for business needs or try :guilabel:`free test API account`. Fill in the required
details and complete the registration process, then copy the provided API key.

In Odoo, open the Settings app, scroll down to the :guilabel:`Integrations` section, and, under
:guilabel:`Barcode Database`, paste the Barcode Lookup :guilabel:`API Key`.

Usage
-----

To fill in product information using Barcode Lookup, create a new product and fill in the
:guilabel:`Barcode` field. The product's details are then automatically imported from Barcode
Lookup, updating the following fields: :guilabel:`Name`, :guilabel:`Price`, :guilabel:`Description`,
:guilabel:`Tax`, :guilabel:`Image`, :guilabel:`Weight`, :guilabel:`Attributes`, :guilabel:`Product
category`, and :guilabel:`Volume`. The fields can then modified as needed.

.. note::
   After the barcode for a product has been entered and the API has pulled its information, updating
   the barcode only changes its internal notes. Other details must be manually updated.

.. seealso::
   :ref:`Create new products during internal transfers using the Barcode Lookup database
   <barcode/setup/barcodelookup>`.
