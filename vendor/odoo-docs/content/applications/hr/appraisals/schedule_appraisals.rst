===================
Schedule appraisals
===================

Odoo's **Appraisals** app helps managers run recurring performance reviews. Each review can include
a self-assessment and can follow any schedule the company sets.

Regular appraisals turn day-to-day work into clear goals and measurable skill targets. They also
supply the objective evidence HR needs for raises or promotions, and keep individual performance
aligned with company KPIs.

Reviews can be :ref:`scheduled automatically <appraisals/auto>` through an :ref:`appraisal plan
<appraisals/appraisal-plan>` that triggers evaluations at set intervals, or :ref:`created manually
<appraisals/manual>` whenever needed—such as before a promotion or department transfer.

.. _appraisals/auto:

Automatic scheduling
====================

To ensure no appraisal is missed, enable automatic scheduling by going to :menuselection:`Appraisals
app --> Configuration --> Settings`.

The :guilabel:`Appraisals Plan` settings determine the frequency with which appraisals are
scheduled.

.. image:: schedule_appraisals/appraisal-settings.png
   :alt: The appraisals sections with the timeline filled in and 360 feedback enabled.

.. _appraisals/appraisal-plan:

Appraisals plans
----------------

By default, appraisals are preconfigured to be automatically created six months after an employee is
hired, with a second appraisal exactly six months after that.

Once those two initial appraisals have been completed in the employee's first year, following
appraisals are only created once a year (every twelve months).

To modify this schedule, change the number of months in the blank fields under the
:guilabel:`Appraisals Plans` section.

.. important::
   Changing the :guilabel:`Appraisals Plans` field updates **every** employee record whose
   :guilabel:`Next Appraisal Dates` is empty.

Appraisals automation
---------------------

Click the checkbox next to :guilabel:`Appraisals Automation` to have Odoo automatically schedule
*and* confirm appraisals.

Appraisals are scheduled according to the :ref:`appraisal plan <appraisals/appraisal-plan>`.

.. _appraisals/manual:

Manually schedule an appraisal
==============================

Managers can schedule an appraisal at any time, outside the regular cycle.

For example, if an employee is promoted, or transfers to a new role or a new department, an
appraisal is scheduled to assess performance in the current role.

To create a new appraisal, open the :menuselection:`Appraisals` app, and click the :guilabel:`New`
button in the upper-left corner. This opens a blank :guilabel:`Appraisals` form.

First, select the employee being evaluated in the :guilabel:`Employee to review` field using the
drop-down menu. Once an employee is selected, their manager populates the :guilabel:`Appraisers`
field. The :guilabel:`Job` and :guilabel:`Department` fields are populated according to the
information on the employee record.

The :guilabel:`Appraisal Date` is when the appraisal is scheduled to be completed. The default
deadline is one month from the current date, but can be adjusted using the calendar selector.

Once the appraisal is marked as complete, a :guilabel:`Next Appraisal Date` field appears, and is
populated with the date of the next appraisal. If there is an :ref:`appraisal plan
<appraisals/appraisal-plan>` configured, the :guilabel:`Next Appraisal Date` field displays
:guilabel:`Ongoing`. This indicates that the following appraisal will be scheduled according to the
appraisal schedule.

Last, select the desired :guilabel:`Template`. The :guilabel:`Default` template populates this field
by default, and is created when the **Appraisals** app is installed. Using the drop-down menu,
select a different template, if desired.

Once the information in the top-half of the :guilabel:`Appraisals` form is complete, click the
:guilabel:`Confirm` button in the upper-left corner. The appraisal is scheduled, the employee and
any other appraisers are notified, and both the employee and appraisers can start to fill out the
appraisal.

Two additional fields appear once the appraisal is confirmed: a :guilabel:`Target Job` and a
:guilabel:`Final Rating` field. The :guilabel:`Target Job` allows the manager to select a job
position the employee may be working towards. When a job position is selected in this field, any
required skills for the job appear in the *Skills* tab. This aids in seeing where the employee
stands in regards to the job requirements :doc:`during the appraisal <new_appraisals>`. The
:guilabel:`Final Rating` field is only populated after the appraisal is complete.

.. image:: schedule_appraisals/new-appraisal.png
   :alt: A new appraisal form with the top half filled out.
