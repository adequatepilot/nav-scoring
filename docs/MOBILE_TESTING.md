# Mobile Testing Guide - NAV Scoring System

## Quick Mobile Testing Using Chrome DevTools

### Prerequisites
- Chrome or Edge browser
- Running NAV Scoring application (http://localhost:8000)

### Steps to Test

#### 1. Open Chrome DevTools
- Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
- Click the "Device Toggle" button (top-left of DevTools) or `Ctrl+Shift+M`

#### 2. Select Mobile Device
- At the top of the page, click the device dropdown (usually says "Responsive")
- Select:
  - **iPhone 12**: 390 × 844px (recommended)
  - **iPhone X**: 375 × 812px
  - **Pixel 5**: 393 × 851px
  - **iPad**: 810 × 1080px

#### 3. Test Hamburger Menu
- ✅ **Desktop mode (>768px)**: Hamburger button should be **hidden**
  - Navigation links visible horizontally
  - Navigation bar shows: `Dashboard > Results > Members > Pairings > Config > NAVs > Logout`
  
- ✅ **Mobile mode (<768px)**: Hamburger button should be **visible**
  - Button displays as `☰` in top-left corner
  - Navigation links should be hidden
  - Click the `☰` button
  - Sidebar overlay should slide in from left
  - Click any navigation link or outside to close

#### 4. Test NAV Management Page
- Navigate to `/coach/navs`
- Should see 2 large cards:
  1. **✈️ Airports** - "Manage departure airports and their configuration"
  2. **🗺️ NAV Routes** - "Manage navigation routes, checkpoints, and secrets"
- No "Start Gates", "Checkpoints", or "Secrets" cards
- Click each card - should navigate to respective detail pages

#### 5. Test SIU Branding
- Login page: Logo placeholder (🦅) should display in maroon (#8B0015)
- Navigation bar: Should be maroon color
- Buttons: Should be maroon with gradient
- Form focus: Should show maroon border and shadow

#### 6. Test Responsive Layout
- **Resize to different widths**:
  - 320px (small phone): All elements should stack
  - 480px (medium phone): Cards should be full width
  - 768px (tablet): Hamburger disappears, inline nav appears
  - 1024px (desktop): Full layout with inline navigation

### Test Cases

#### Desktop Layout (≥768px)
```
✅ Hamburger button hidden
✅ Navigation links visible inline
✅ All content properly aligned
✅ Cards display in grid
✅ Forms fully responsive
```

#### Mobile Layout (<768px)
```
✅ Hamburger button (☰) visible
✅ Navigation links hidden
✅ Sidebar opens on hamburger click
✅ Sidebar closes on link click
✅ Sidebar closes on overlay click
✅ Content readable without horizontal scroll
✅ Buttons are full-width on mobile
✅ Tables scroll horizontally if needed
```

#### Color Scheme Verification
```
✅ Navigation bar: Maroon (#8B0015)
✅ Buttons: Maroon gradient
✅ Links: Maroon color
✅ Form focus: Maroon border and shadow
✅ Table headers: Maroon accent
✅ Alerts: Color-coded (red/green/blue)
```

### Common Issues & Solutions

#### Issue: Hamburger button appears on desktop
**Solution**: Check Chrome DevTools zoom level (should be 100%)

#### Issue: Navigation links appear twice
**Solution**: Clear browser cache (Ctrl+Shift+Delete) and reload

#### Issue: Sidebar doesn't close
**Solution**: Check browser console for JavaScript errors (F12 → Console)

#### Issue: Styling looks different from localhost
**Solution**: 
- Ensure static files are served (`/static/styles.css`)
- Check for CSS cache issues
- Hard reload: `Ctrl+Shift+R` (Windows) / `Cmd+Shift+R` (Mac)

### Testing on iOS Safari

#### Setup
1. Open Safari on your iOS device
2. Navigate to: `http://<your-computer-ip>:8000`
3. Note: Computer and iPhone must be on same network

#### Test Points
- ✅ Hamburger button appears correctly
- ✅ Sidebar opens/closes smoothly
- ✅ Touch interactions work
- ✅ No horizontal scroll issues
- ✅ Text is readable without pinch-zoom
- ✅ Buttons are easily tappable (44x44px minimum)

#### Known iOS Behaviors
- Viewport may be slightly different from Chrome DevTools
- Try rotating device between portrait and landscape
- Check SafeArea insets on notched devices (iPhone X/12/13)

### Performance Testing

#### Check Network Tab
1. Open DevTools Network tab
2. Reload page
3. Verify:
   - `styles.css` loads (4.7KB)
   - All templates load
   - No 404 errors
   - No failed requests

#### Check Console Tab
1. Open DevTools Console tab
2. Look for errors or warnings
3. Should see no red error messages
4. JavaScript should execute without errors

### Lighthouse Audit

1. Open Chrome DevTools
2. Go to "Lighthouse" tab
3. Click "Analyze page load"
4. Check scores:
   - Performance
   - Accessibility
   - Best Practices
   - SEO

### Screenshot Testing

#### Desktop Screenshot
1. Chrome DevTools → Device: Desktop (1920x1080)
2. Right-click → Capture screenshot
3. Save as `desktop-view.png`

#### Mobile Screenshot
1. Chrome DevTools → Device: iPhone 12
2. Right-click → Capture screenshot
3. Save as `mobile-view.png`

#### Tablet Screenshot
1. Chrome DevTools → Device: iPad
2. Right-click → Capture screenshot
3. Save as `tablet-view.png`

### Automated Testing (Optional)

If you want automated mobile testing:

```bash
# Install dependencies
npm install -g puppeteer

# Run mobile test
node test-mobile.js
```

### Sign-Off Checklist

Before declaring testing complete:

- [ ] Hamburger menu appears on mobile (<768px)
- [ ] Hamburger menu hidden on desktop (≥768px)
- [ ] Sidebar opens and closes smoothly
- [ ] All navigation links work
- [ ] NAV page shows only 2 cards
- [ ] SIU maroon color scheme applied
- [ ] Forms are usable on mobile
- [ ] No JavaScript console errors
- [ ] No missing images or files
- [ ] Tested on iOS Safari (if available)
- [ ] All existing features still work

---

## Quick Reference: Responsive Breakpoint

```
Mobile-first approach:
- Default: Mobile (<768px) - Hamburger menu visible
- Tablet/Desktop (≥768px): Inline navigation visible
```

```css
/* In base.html and styles.css */
@media (max-width: 768px) {
    .hamburger { display: block; }
    .navbar-links { display: none; }
}

@media (min-width: 769px) {
    .hamburger { display: none; }
    .navbar-links { display: flex; }
}
```

---

## Notes

- Application reloads at: `http://localhost:8000`
- Login: Use your coach or team member credentials
- Database: Persists across Docker restarts
- Static files: Located at `/app/static/` in container

---

Generated: February 12, 2025
Last Updated: UI/UX Implementation Complete
