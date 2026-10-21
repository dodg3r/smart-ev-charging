# Smart EV Charging

Home Assistant custom integration based on the existing HiBerry Node-RED charging logic.

## v0.2.0

This release is **read-only**.

It reads the same types of inputs as the Node-RED flow and calculates:

- per-phase main-fuse load balancing
- requested charging current
- charger start/stop decision preview
- soft start / ramping
- solar-only charging
- home-battery support logic
- cloud pause
- session/resting/full-charge handling
- Automatic / Cheap Time decision hooks
- compact debug output

It **does not call any charger service**.

### Important

The supplied Node-RED export reads `global.get("nordpool_cheapest_plan")`, but the
export does not contain the code that creates that Nordpool plan. Therefore
v0.2.0 deliberately does not invent a replacement planner. `Cheap Time` and the
price-driven part of `Automatic` will report that the planner is not yet ported.

The next step is to port the exact Nordpool-plan generator from the current
Node-RED setup, then compare Smart EV Charging and Node-RED side by side.
