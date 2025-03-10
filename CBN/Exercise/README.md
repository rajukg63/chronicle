Students should map the following raw log entries to these UDM fields:

GENERIC_EVENT -> metadata.event_type
Ping -> metadata.vendor_name
AIC -> metadata.product_name
recordedAt -> metadata.event_time
actor.user.name -> principal.user.userid

In the second exercise, modify the above to code:
actor.user.name -> principal.user.email_address
result.status -> tsecurity_result.action

