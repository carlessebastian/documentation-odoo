========================
Odometer analysis report
========================

The **Fleet** app allows for analysis of all odometer readings logged in the system, which managers
can use to determine the use, in terms of mileage, of their vehicles.

This information can aid in decision making when determining which vehicles to add to the fleet, or
which vehicles to retire. Additionally, this information can assist when performing routine audits,
ensuring vehicles used adhere to company policy, and accurate records are being kept.

For the *Odometer Analysis* report to deliver reliable, meaningful insights, ensure odometer
readings are updated regularly for every vehicle. Typically, odometer values are updated when a
vehicle is :ref:`added to the fleet <fleet/new_vehicle/general-info>`, and when any :ref:`services
<fleet/service-form>` are performed on a vehicle.

.. note::
   Many companies follow internal policies for routine odometer updates. For example, delivery
   trucks may require weekly odometer reporting, while employee vehicles might only need to report
   mileage on a monthly basis.

.. _fleet/odometers/total-costs:

Monthly odometer values
=======================

To view the *Odometer Analysis* report, navigate to :menuselection:`Fleet app --> Reporting -->
Odometers`. The default report shows a line chart of the odometer values, grouped by month, then
vehicle category.

The mileage shown is the odometer value *per month*, not the :ref:`total accumulated mileage
<fleet/odometers/by-vehicle>` each month. This report allows managers to see which vehicle
categories are being driven the most on a monthly basis.

The data in this report may aid managers when performing audits, since the data from this report can
be compared to the expected mileage, such as round trip distances for repairs or deliveries. This
may help ensure vehicles are not being used for non-work purposes. Additionally, the total mileage
driven for employee vehicles may be compared to the expected mileage according to the
:ref:`home-work distance <employees/location>` configured on employee records.

.. example::
   In this report, it is possible to determine that the *Delivery Trucks* have both the highest and
   most consistent mileage, month to month.

   .. image:: odometers/odometers-monthly.png
      :alt: The total odometer value per month for all vehicles.

.. _fleet/odometers/by-vehicle:

Total odometer values
=====================

To view the total odometer value for all vehicles in the fleet, open the *Odometer Analysis* report
by navigating to :menuselection:`Fleet app --> Reporting --> Odometers`. Click on the
:guilabel:`Measures` button, and select :guilabel:`Odometer Value` from the drop-down menu.

This presents all the odometer values, grouped by month and category. This allows companies to learn
which vehicle type logs the most miles, and is therefore on the road or in use the most. This
information may aid managers in determining which vehicles add the most value and should be kept,
and which vehicles should be retired.

.. example::
   In this report, it can be determined that the *Delivery Trucks* (the blue line in the graph)
   drive the most miles each month, more than double the combined mileage of the other vehicles. The
   *Repair Vans* and *Employee Cars* both drive a comparable amount of miles each month, with
   *Employee Cars* logging slightly more miles, overall.

     .. image:: odometers/odometer-total.png
        :alt: The odometer report showing total odometer values, by month and category.
