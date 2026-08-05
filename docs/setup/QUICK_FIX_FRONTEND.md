# Quick Fix: Frontend on Render

## The Problem
You have 2 frontend services on Render:
1. **land-scanner-prototype** (static site)
2. **land-scanner-prototype-backend** (also serves frontend)

This causes issues because the separate frontend can't call the backend API (different domain).

---

## Solution: Choose One

### ✅ RECOMMENDED: Delete Separate Frontend Service

1. Go to https://dashboard.render.com
2. Click **land-scanner-prototype** (the static site one)
3. Scroll to bottom
4. Click **Delete Web Service** (or similar)
5. Confirm deletion
6. Wait 1 minute
7. Access at: **https://land-scanner-prototype-backend.onrender.com**
8. Done! Frontend and backend work together

**Result**: Everything at one URL, no CORS issues, no environment variables needed

---

### ALTERNATIVE: Hardcode Backend URL in Frontend

If you MUST keep separate frontend service:

1. Edit `frontend/js/app.js`
2. Find line 6: `const API_BASE = window.location.origin;`
3. Replace with: `const API_BASE = 'https://land-scanner-prototype-backend.onrender.com';`
4. Commit: `git add frontend/js/app.js && git commit -m "Fix: Hardcode backend URL"`
5. Push: `git push origin main`
6. Trigger rebuild on Render frontend service
7. Wait 2 minutes
8. Test at: https://land-scanner-prototype.onrender.com

**Result**: Frontend works, but two separate services to manage

---

## Which Should You Choose?

| Aspect | Option 1 (Delete Separate) | Option 2 (Hardcode URL) |
|--------|--------------------------|----------------------|
| Setup | Easiest - delete 1 service | Harder - code change |
| Maintenance | Simple | Complex |
| CORS Issues | ✓ None | ✓ None |
| Speed | Faster | Same |
| Flexibility | Limited but works | Can scale separately |
| Recommendation | ⭐⭐⭐⭐⭐ Best | ⭐⭐ If you need it |

**Recommended**: Go with Option 1 (delete separate frontend service)

---

## Do Frontend Environment Variables Work on Render?

**NO** - Static sites on Render:
- Don't have a build process
- Don't have a runtime
- Can't inject environment variables
- Just serve files as-is

So don't add environment variables to the static site service - they won't be used.

---

## After Choosing Your Solution

1. Commit any changes
2. Push to GitHub
3. Wait for Render rebuild
4. Test:
   - Frontend loads at: https://land-scanner-prototype-backend.onrender.com (Option 1) or https://land-scanner-prototype.onrender.com (Option 2)
   - Can draw polygon
   - Can click "Analyze"
   - Sees results

---

**Choose Option 1 (recommended) and you're done!**
