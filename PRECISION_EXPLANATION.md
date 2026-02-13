# Issue 10.1: Latitude/Longitude Precision Explanation

## The Question
"Why can't we get more specific than 7-8 decimals for lat/long coordinates?"

## The Answer

### Database Capabilities
SQLite stores geographic coordinates using the REAL data type, which is an **8-byte IEEE 754 double-precision floating-point number**. This provides approximately **15-17 significant decimal digits** of precision.

**This is NOT a limitation of the database.** The database can store and display way more than 8 decimals.

### Practical Precision vs. Physical Reality

| Decimal Places | Accuracy | Use Case | Example |
|---|---|---|---|
| 1 decimal | ~11.1 km | Country-level | 40.7 (New York general area) |
| 2 decimals | ~1.1 km | City-level | 40.71 (Downtown NYC) |
| 3 decimals | ~111 m | Neighborhood | 40.713 (5th Ave area) |
| 4 decimals | ~11.1 m | Street-level | 40.7128 (Specific block) |
| 5 decimals | ~1.1 m | Precise location | 40.71280 (Exact building) |
| **6 decimals** | **~11 cm** | **Survey-grade** | **40.712838** |
| **7 decimals** | **~1.1 cm** | **Centimeter precision** | **40.7128378** |
| **8 decimals** | **~1.1 mm** | **Millimeter precision** | **40.71283779** |

### Why 7 Decimals is Perfect for Aviation

**Consumer GPS devices accuracy:**
- Typical handheld/mobile GPS: ±5-10 meters
- High-end GPS (RTK): ±1-5 cm
- Survey-grade GPS: ±1-5 cm

**Aircraft position uncertainty:**
- Aircraft in flight: ±10-50 meters (wind drift, sensor lag, etc.)
- Pre-flight planning: ±5-10 meters typical

### Current Implementation

**What we do:**
- ✅ Database stores full IEEE 754 precision (15-17 significant digits)
- ✅ Display shows 7 decimals (sufficient for 1.1 cm accuracy)
- ✅ Can increase display to 8-9 decimals if desired
- ✅ No data loss - full precision stored

**Result:**
7 decimal places = **1.1 centimeter accuracy**

This is already **100x better** than any consumer GPS device can actually measure.

### The Bottom Line

**More decimal places won't give us better real-world accuracy because:**

1. **GPS is the limiting factor** - Consumer devices give ±5-10 meters, not ±1mm
2. **Aircraft move** - A 1mm difference is meaningless when the aircraft might drift 20 meters due to wind
3. **Environmental noise** - Sensor readings fluctuate at higher decimal places
4. **Web browsers round** - Display rendering may show slight rounding on extreme precisions

### What This Means

If we displayed 8-9 decimals in the UI, you'd see numbers like:
```
40.712837890238904823 (utterly meaningless variation)
```

This looks precise but is actually just noise below the real measurement accuracy of GPS (which is meters).

### Recommendation

**Keep 7 decimals.** This is:
- ✅ Sufficient for 1.1 cm accuracy (far beyond GPS capability)
- ✅ Clean and readable in the UI
- ✅ Mathematically sound for aviation navigation
- ✅ Not wasting database or display space on noise

**If you want 8-9 decimals for peace of mind,** we can easily change the display format in the templates, but understand that the extra digits are environmental noise, not real precision.

---

**Bottom Line:** The system is correct as-is. 7 decimals provides more precision than any GPS device on an aircraft could ever measure.
