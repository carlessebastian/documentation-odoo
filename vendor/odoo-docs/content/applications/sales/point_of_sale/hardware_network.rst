:show-content:

====================
Hardware and network
====================

Odoo Point of Sale supports integration with a variety of hardware, including :doc:`payment
terminals <payment_methods/terminals>`, cash drawers, :doc:`customer displays
<hardware_network/customer_display>`, :doc:`scales <hardware_network/scale>`, :doc:`barcode scanners
</applications/inventory_and_mrp/barcode/setup/hardware>`, :doc:`receipt printers
<hardware_network/receipt_printers>`, and in-store :doc:`electronic shelf labels
<hardware_network/electronic_labels>`.

.. cards::

   .. card:: Local Network Access
      :target: hardware_network/pos_lna

      Enable direct browser communication with local hardware, like ePOS printers, without requiring
      SSL certificates.

   .. card:: IoT system connection
      :target: hardware_network/pos_iot

      Link your POS to an IoT system to connect and coordinate hardware peripherals like printers,
      scales, and scanners.

   .. card:: Receipt printers
      :target: hardware_network/receipt_printers

      Configure directly supported printers and identify which models require an IoT system for
      connection.

   .. card:: Electronic shelf labels
      :target: hardware_network/electronic_labels

      Integrate with the Pricer platform to configure and update digital shelf labels.

   .. card:: Customer display
      :target: hardware_network/customer_display

      Set up a secondary screen to show order details and prices to customers during checkout.

   .. card:: Scale
      :target: hardware_network/scale

      Configure and use scales in the POS, including settings for European legal requirements.

   .. card:: Self-signed certificate for ePOS printers
      :target: hardware_network/epos_ssc
      :large:

      Generate and install self-signed SSL certificates for secure HTTPS communication with ePOS
      printers.

.. toctree::
   :titlesonly:

   hardware_network/pos_lna
   hardware_network/pos_iot
   hardware_network/receipt_printers
   hardware_network/electronic_labels
   hardware_network/customer_display
   hardware_network/scale
   hardware_network/epos_ssc
