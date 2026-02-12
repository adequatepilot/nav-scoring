# SIU Logo and Images Directory

This directory is for storing SIU branding assets and images used throughout the NAV Scoring System.

## Placeholder Logo

Currently, the application uses an eagle emoji (🦅) as a placeholder for the SIU Salukis logo. 

## Logo Placement

Logos appear on:
1. **Login Page** - Top center/left of login form
2. **Coach Dashboard Header** - Left side of navbar
3. **Team Dashboard Header** - Left side of navbar

## Adding Real SIU Logo

When ready to add the actual SIU logo:

1. **Place logo file here**: `static/images/siu-logo.png` or `siu-logo.svg`
2. **Update HTML templates** to reference the image instead of emoji:
   ```html
   <img src="/static/images/siu-logo.png" alt="SIU" class="siu-logo-img">
   ```
3. **CSS for logo image** (add to base.html or styles.css):
   ```css
   .siu-logo-img {
       height: 50px;
       width: auto;
       max-width: 200px;
   }
   ```

## Recommended Logo Files

- **Logo file**: `siu-logo.png` (transparent PNG recommended)
- **Logo size**: 200x200px or larger (will scale automatically)
- **Format**: PNG with transparency for best results

## Directory Structure

```
static/
├── images/
│   ├── README.md (this file)
│   ├── siu-logo.png (add when available)
│   └── siu-logo.svg (optional vector version)
└── styles.css
```

## SIU Colors

- **Primary Maroon**: #8B0015 (used in navbar and buttons)
- **Secondary Maroon**: #5D000F (used for hover/active states)
- **Accent Gold**: #DAA520 (available for highlights)
- **White**: #FFFFFF (text and backgrounds)

These colors are defined in `static/styles.css` as CSS variables in the `:root` section.
