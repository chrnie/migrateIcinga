# Icinga2 migration helpers

These scripts are intended to help you migrating an old icinga2 to a new instance.
It consists of: 

  * migrateServices.py
    * copy Services, that have been created by icinga2 api (including last state, last output, last_perfdata)
  * migrateDowntimes.py*
    * Copy downtimes, host by host, service by service
  * migrateAcks.py
    * acknowledge unacknowledged services/hosts on the new system that have been acknowledged on the old system.
