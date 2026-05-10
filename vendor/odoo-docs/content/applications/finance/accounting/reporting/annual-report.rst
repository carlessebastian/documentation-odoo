===================
Annual/Audit report
===================

Annual reports document annual financial performance, operational challenges, and organizational
achievements for stakeholder review.

Odoo :ref:`generates annual reports <accounting/annual-report/creation>` from pre-configured
templates. Users can :ref:`edit and customize <accounting/annual-report/edit>` content, :ref:`add
more content or upload PDF files <accounting/annual-report/additional-content>`, and :ref:`export
the report as a PDF <accounting/annual-report/export>` for distribution.

.. note::
   The annual report is edited using the :doc:`Knowledge app <../../../productivity/knowledge>`
   interface from within the Accounting app.

.. _accounting/annual-report/creation:

Create an annual report
=======================

To create an annual report, follow these steps:

#. Go to :menuselection:`Accounting --> Review --> Annual Report` and click :guilabel:`New`.
#. In the :guilabel:`Create an Annual Report` window, enter a :guilabel:`Title` and, if necessary,
   update the start and end :guilabel:`Dates` of the period covered by the report.
#. Update the :guilabel:`Responsibles` field to let other users access and edit the report, if
   needed.
#. Click :guilabel:`Save`.

A :guilabel:`Draft` annual report card is then created in the :guilabel:`Annual Reports` Kanban
view.

.. note::
   - Clicking the card opens the annual report in the :ref:`editable view
     <accounting/annual-report/edit>`.
   - The annual report is stored in the :doc:`Knowledge app <../../../productivity/knowledge>`,
     under the :guilabel:`Private` category in the sidebar tree, making the editable report visible
     only to its creator. If additional users are added to the :guilabel:`Responsibles` field, the
     annual report is then moved to the :guilabel:`Shared` category, allowing those users to access
     it as well.

.. _accounting/annual-report/edit:

Edit an annual report
=====================

.. note::
   To modify the annual report's :guilabel:`Title`, :guilabel:`Dates`, or :guilabel:`Responsibles`,
   go to :menuselection:`Accounting --> Review --> Annual Report`, click the :icon:`fa-ellipsis-v`
   :guilabel:`(vertical ellipsis)` icon of the annual report card, and select :guilabel:`Configure`.

To edit the content of the annual report, go to :menuselection:`Accounting --> Review --> Annual
Report`, then click on the annual report card to open it.

In the sidebar tree, hover over the new annual report and click the :icon:`fa-caret-right`
:guilabel:`(right arrow)` icon to the left of the title to display the different sections. The
detailed view appears in the main editing area. Click any item in the sidebar or main view to open
it for editing:

- :guilabel:`Attestation`: Use the :icon:`fa-toggle-on` :guilabel:`(toggle-on)` or
  :icon:`fa-toggle-off` :guilabel:`(toggle-off)` icons to show or hide attestations, which contain
  dynamic text. Dates and company values are automatically updated when the final PDF report is
  generated, which includes only attestations with the toggle enabled.

  .. note::
     Attestations can be signed electronically by clicking :guilabel:`SIGNATURE`. For users who have
     previously signed documents in Odoo, click :guilabel:`Sign`. For first-time signers,
     :ref:`define a signature <sign/sign-document/initials-signature>`, then click :guilabel:`Adopt
     & Sign`.

- :guilabel:`Balance Sheet`: Click :guilabel:`Customize` to open the :guilabel:`Balance Sheet` and
  customize it using filters and options. Any configurations performed are reflected in the
  :ref:`exported PDF report <accounting/annual-report/export>`.
- :guilabel:`Profit and Loss`: Click :guilabel:`Customize` to open the :guilabel:`Profit and Loss`
  statement and customize it using filters and options. Any configurations performed are reflected
  in the :ref:`exported PDF report <accounting/annual-report/export>`.
- :guilabel:`Annexes`: Displays :ref:`additional items
  <accounting/annual-report/additional-content>` included in the report.
- :guilabel:`Supporting Documents`: Allows :ref:`uploaded PDF files
  <accounting/annual-report/additional-content>` to be included in the report.

To remove items from the annual report, drag and drop them into :icon:`fa-trash` :guilabel:`Open the
Trash` in the sidebar, or hover over the item in the main view and click the :icon:`fa-trash`
:guilabel:`(trash)` icon.

.. tip::
   - Drag and drop items in the sidebar or main view to reorder them.
   - To create a new article, hover over a section in the sidebar and click the :icon:`fa-plus`
     :guilabel:`(plus)` icon that appears next to it. The article is then nested under the relevant
     section.
   - To show or hide sub-articles, click :icon:`fa-sitemap` :guilabel:`Show sub-articles` or
     :icon:`fa-sitemap` :guilabel:`Hide sub-articles` in the main view.

.. _accounting/annual-report/additional-content:

Additional content
------------------

The :guilabel:`Annexes` section contains additional items, such as customizable accounting reports,
and articles with sections or tables to complete. Review and delete any items that should not be
included in the final report.

To add additional annexes, click :guilabel:`Annexes` in the sidebar, then, in the main view, choose
one of the following options:

- :guilabel:`Load a Template`: Click to select extra items not included by default. Complete the
  sections, disable the :icon:`fa-toggle-on` :guilabel:`(toggle-on)` icons to hide unnecessary
  parts, and click :guilabel:`Load Template`.
- :guilabel:`Add an Article`: Click to create a blank article to complete manually.

In the :guilabel:`Supporting Documents` section, click :guilabel:`Upload files` to include
additional PDF files in the annual report.

.. _accounting/annual-report/export:

Export an annual report
=======================

To export the annual report as a PDF, follow these steps:

#. Go to :menuselection:`Accounting --> Review --> Annual Report`, then click on the annual report
   card to open it in the editable view.
#. Click on the upper-most level of the annual report in the sidebar tree.
#. Click the :icon:`fa-ellipsis-v` :guilabel:`(vertical ellipsis)` icon in the top-right corner and
   select :icon:`fa-file-pdf-o` :guilabel:`Download Annual Report`.
#. In the :guilabel:`Download Annual Report` window, disable the :icon:`fa-toggle-on`
   :guilabel:`(toggle-on)` icons to exclude sub-articles and PDF files, if needed.
#. Click :guilabel:`Download PDF`.

Alternatively, go to :menuselection:`Accounting --> Review --> Annual Report` and click
:guilabel:`Print` on the annual report card. This option includes sub-articles and uploaded PDF
files by default.

.. tip::
   The logo configured in the :ref:`company form <general/companies/company>` is displayed on the
   cover page of the annual report.

To mark an annual report as :guilabel:`Done` or to delete it, go to :menuselection:`Accounting -->
Review --> Annual Report`, click the :icon:`fa-ellipsis-v` :guilabel:`(vertical ellipsis)` icon on
the report card, then select :guilabel:`Set to Done` or :guilabel:`Delete`, as appropriate.
