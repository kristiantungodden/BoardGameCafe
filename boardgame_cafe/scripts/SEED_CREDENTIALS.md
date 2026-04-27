# Demo Seed Credentials

Run the seed script to populate the database:

```bash
python boardgame_cafe/scripts/seed_demo_data.py
```

---

## Users

### Admin
| Name  | Email               | Password    |
|-------|---------------------|-------------|
| admin | admin@example.com   | Adminpw123  |

### Stewards (Staff)
| Name        | Email                    | Password   |
|-------------|--------------------------|------------|
| steward     | steward@example.com      | Stewardpw  |
| Maria Lund  | maria.lund@example.com   | Stewardpw  |

### Customers
| Name         | Email                        | Password   |
|--------------|------------------------------|------------|
| a *(quick)*  | a@a.a                        | aaaaaaaa   |
| b *(quick)*  | b@b.b                        | bbbbbbbb   |
| Emma Hansen  | emma.hansen@example.com      | Password1  |
| Lars Olsen   | lars.olsen@example.com       | Password1  |
| Sofie Berg   | sofie.berg@example.com       | Password1  |
| Jonas Vik    | jonas.vik@example.com        | Password1  |

---

## What's seeded

| Data             | Details                                                                 |
|------------------|-------------------------------------------------------------------------|
| Games            | 14 titles with pricing, images and tags                                 |
| Tables           | T1–T8 across 2 floors; T6 is in maintenance                            |
| Game copies      | 31 copies; 1 in maintenance, 1 lost                                     |
| Bookings         | 4 upcoming confirmed, 1 seated (now), 4 past completed, 1 cancelled, 1 no-show |
| Payments         | Paid for completed/seated · Refunded for cancelled/no-show · Calculated for confirmed |
| Incidents        | 2 open incidents on damaged/maintenance copies                          |
| Announcements    | 1 published (Grand Opening), 1 draft (Game Night)                      |
