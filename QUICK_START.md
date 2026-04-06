# 🎯 QUICK START GUIDE - 3D Restaurant System with Claude Code

## HOW TO USE THIS WITH CLAUDE CODE

### Step 1: Install Claude Code
```bash
# If you don't have Claude Code yet:
# Download from: https://claude.ai/code

# Or install via npm (if available in your region):
npm install -g claude-code
```

### Step 2: Start Claude Code
```bash
# Open your terminal and run:
claude-code

# Or if you're using the desktop app, just launch it
```

### Step 3: Copy the Prompt
1. Open the file: `CLAUDE_CODE_PROMPT.txt`
2. Copy the ENTIRE contents
3. Paste into Claude Code
4. Press Enter

### Step 4: Claude Code Will Build Everything
Claude Code will create:
- ✅ Complete backend API (Node.js + Express)
- ✅ PostgreSQL database setup
- ✅ Admin dashboard (React app)
- ✅ Customer menu viewer (React app)
- ✅ 3D model viewer with AR support
- ✅ File upload system
- ✅ All necessary configuration files

### Step 5: Follow Claude Code's Instructions
Claude Code will guide you through:
1. Installing dependencies
2. Setting up the database
3. Running the backend server
4. Running the frontend apps
5. Testing the system

---

## WHAT YOU'LL GET

### 1. Backend API
```
http://localhost:3000/api/menu       - Menu management
http://localhost:3000/api/upload     - File uploads
http://localhost:3000/api/orders     - Order handling
```

### 2. Admin Dashboard
```
http://localhost:3001
- Upload 3D models
- Manage menu items
- Set prices and descriptions
- Control availability
```

### 3. Customer Menu
```
http://localhost:3002
- Browse 3D food models
- Rotate and zoom
- View in AR (on mobile)
- Add to cart and order
```

---

## SCANNING YOUR FOOD

### Recommended Apps (Easiest Method):

**For iPhone/iPad:**
```
1. Polycam (Best option)
   - Download: App Store
   - Has LiDAR support
   - Exports GLB directly
   - Free tier available
   
2. 3D Scanner App
   - Uses LiDAR (iPhone Pro models)
   - Quick scanning
   - Good quality
```

**For Android:**
```
1. Polycam
   - Photo-based scanning
   - Good results
   
2. RealityScan
   - By Epic Games
   - Free
   - High quality
```

### Scanning Process:
```
1. Place food on plain surface (white/neutral background)
2. Open scanning app
3. Walk around food in a circle (360°)
4. Take 20-30 photos OR use auto-scan
5. App processes into 3D model
6. Export as GLB format
7. Upload to your system via admin dashboard
```

---

## FILE FORMATS

### Supported 3D Formats:
- ✅ .GLB (recommended) - Single file with everything
- ✅ .GLTF - JSON + separate texture files

### Supported Image Formats (Thumbnails):
- ✅ .JPG
- ✅ .PNG

### File Size Limits:
- 3D Models: Up to 50MB
- Thumbnails: Up to 5MB
- Recommended model size: Under 10MB for best performance

---

## TYPICAL WORKFLOW

### For Restaurant Staff:
```
1. Prepare dish as you would serve it
2. Scan with smartphone (Polycam app)
3. Export as GLB
4. Log into admin dashboard
5. Upload GLB file
6. Add details:
   - Dish name: "Deluxe Burger"
   - Category: "Main Course"
   - Price: $12.99
   - Description: "Juicy beef patty..."
   - Allergens: ["gluten", "dairy"]
7. Save
8. Model appears in customer menu immediately
```

### For Customers:
```
1. Open menu website on phone/tablet/kiosk
2. Browse dishes with 3D previews
3. Tap any dish to see full 3D view
4. Rotate and zoom to inspect
5. Tap "View in AR" (mobile only)
6. See dish on your table in real size
7. Add to cart
8. Place order
```

---

## TROUBLESHOOTING

### If Claude Code doesn't install packages:
```bash
# Manually install backend dependencies:
cd backend
npm install express pg multer cors dotenv sharp

# Manually install frontend dependencies:
cd frontend/admin
npm install react three @react-three/fiber @google/model-viewer axios

cd ../customer
npm install react three @react-three/fiber @google/model-viewer axios
```

### If 3D models don't load:
- Check file format is .glb or .gltf
- Verify file size under 50MB
- Check browser console for errors
- Try different browser (Chrome recommended)
- Make sure WebGL is enabled

### If AR doesn't work:
- Requires iPhone 6S+ with iOS 12+
- Requires Android 8+ with ARCore support
- Must use HTTPS in production
- Safari on iOS or Chrome on Android

### If upload fails:
- Check file permissions on uploads folder
- Verify multer middleware is configured
- Check file size limits
- Verify file extension is allowed

---

## NEXT STEPS AFTER SETUP

1. **Test with sample models:**
   - Download free GLB models: https://sketchfab.com/feed
   - Filter by "Downloadable" and "GLB"
   - Search for "food" models

2. **Scan your first dish:**
   - Use Polycam app
   - Follow scanning tips
   - Upload to system

3. **Customize the design:**
   - Modify colors in CSS
   - Change layout
   - Add your restaurant branding

4. **Deploy to production:**
   - Deploy backend to: Heroku, Railway, or DigitalOcean
   - Deploy frontend to: Vercel, Netlify, or AWS
   - Set up domain name
   - Configure HTTPS (required for AR)

---

## COST BREAKDOWN

### Free Tier:
- Backend: Railway/Render free tier
- Frontend: Vercel/Netlify free tier
- Database: PostgreSQL free tier (Railway/Supabase)
- Scanning: Polycam free tier (3 exports/month)

### Paid (if you scale):
- Polycam Pro: $10/month (unlimited exports)
- Server hosting: $5-20/month
- Domain: $10-15/year
- CDN (optional): $5-10/month

---

## SUPPORT

If you get stuck:
1. Check the README files Claude Code creates
2. Review error messages in terminal
3. Check browser console (F12)
4. Re-prompt Claude Code with specific issues
5. Ask Claude Code: "The 3D models aren't loading, what should I check?"

---

## TIPS FOR SUCCESS

✅ Start with 1-2 menu items to test
✅ Use good lighting when scanning
✅ Plain backgrounds work best
✅ Take plenty of photos (20-30 minimum)
✅ Test on actual devices (phone, tablet, kiosk)
✅ Optimize model sizes before uploading
✅ Keep descriptions short and clear
✅ Use high-quality food photography for thumbnails

❌ Don't scan in poor lighting
❌ Don't move food during scanning
❌ Don't use blurry photos
❌ Don't upload huge model files (>50MB)
❌ Don't skip testing on mobile

---

## YOU'RE READY! 🚀

Copy the prompt from `CLAUDE_CODE_PROMPT.txt` into Claude Code and let it build your system!
