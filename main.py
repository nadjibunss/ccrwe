# -*- coding: utf-8 -*-
import asyncio
import re
import subprocess
import sys
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import os
import traceback
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import database as db
import hashlib
from dotenv import load_dotenv
import platform

# Load environment variables
load_dotenv()

# --- Configuration ---
YOUR_BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_IDS = os.getenv("ADMIN_CHAT_IDS", "").split(",")
IVAS_EMAIL = os.getenv("IVAS_EMAIL")
IVAS_PASSWORD = os.getenv("IVAS_PASSWORD")

# Group IDs (Adjustable via env or hardcoded as defaults)
FORCE_JOIN_GROUPS = [
    {"id": "-1002169357145", "link": "https://t.me/+hd0kQJXgGRgyY2Fh"},
    {"id": "-1002146214331", "link": "https://t.me/+LFEOerK9CPtmMjdh"}
]
OTP_GROUP_ID = "-1001858426230"

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"

POLLING_INTERVAL_SECONDS = 5
STATE_FILE = "processed_sms_ids.json"

# Initialize DB
db.init_db()

# --- Virtual Display for VPS (Linux only) ---
display = None
if platform.system() == 'Linux':
    try:
        from pyvirtualdisplay import Display
        print("🖥️ Starting Virtual Display (Xvfb) for Headed Chrome...")
        display = Display(visible=0, size=(1920, 1080))
        display.start()
    except ImportError:
        print("⚠️ pyvirtualdisplay not found! Install it for VPS support: pip install pyvirtualdisplay")
    except Exception as e:
        print(f"⚠️ Failed to start virtual display: {e}")

# --- Exhaustive Maps ---
COUNTRY_FLAGS_MAP = {
    "Afghanistan": "🇦🇫", "Albania": "🇦🇱", "Algeria": "🇩🇿", "American Samoa": "🇦🇸", "Andorra": "🇦🇩", "Angola": "🇦🇴", "Anguilla": "🇦🇮", "Antigua and Barbuda": "🇦🇬",
    "Argentina": "🇦🇷", "Armenia": "🇦🇲", "Aruba": "🇦🇼", "Australia": "🇦🇺", "Austria": "🇦🇹", "Azerbaijan": "🇦🇿", "Bahamas": "🇧🇸", "Bahrain": "🇧🇭",
    "Bangladesh": "🇧🇩", "Barbados": "🇧🇧", "Belarus": "🇧🇾", "Belgium": "🇧🇪", "Belize": "🇧🇿", "Benin": "🇧🇯", "Bermuda": "🇧🇲", "Bhutan": "🇧🇹",
    "Bolivia": "🇧🇴", "Bosnia": "🇧🇦", "Botswana": "🇧🇼", "Brazil": "🇧🇷", "Brunei": "🇧🇳", "Bulgaria": "🇧🇬", "Burkina Faso": "🇧🇫", "Burundi": "🇧🇮",
    "Cambodia": "🇰🇭", "Cameroon": "🇨🇲", "Canada": "🇨🇦", "Cape Verde": "🇨🇻", "Cayman Islands": "🇰🇾", "CAR": "🇨🇫", "Chad": "🇹🇩", "Chile": "🇨🇱",
    "China": "🇨🇳", "Colombia": "🇨🇴", "Comoros": "🇰🇲", "Congo": "🇨🇬", "DR Congo": "🇨🇩", "Cook Islands": "🇨🇰", "Costa Rica": "🇨🇷", "Croatia": "🇭🇷",
    "Cuba": "🇨🇺", "Cyprus": "🇨🇾", "Czechia": "🇨🇿", "Denmark": "🇩🇰", "Djibouti": "🇩🇯", "Dominica": "🇩🇲", "Dominican Rep": "🇩🇴", "Ecuador": "🇪🇨",
    "Egypt": "🇪🇬", "El Salvador": "🇸🇻", "Equatorial Guinea": "🇬🇶", "Eritrea": "🇪🇷", "Estonia": "🇪🇪", "Ethiopia": "🇪🇹", "Falkland Islands": "🇫🇰", "Faroe Islands": "🇫🇴",
    "Fiji": "🇫🇯", "Finland": "🇫🇮", "France": "🇫🇷", "French Guiana": "🇬🇫", "French Polynesia": "🇵🇫", "Gabon": "🇬🇦", "Gambia": "🇬🇲", "Georgia": "🇬🇪",
    "Germany": "🇩🇪", "Ghana": "🇬🇭", "Gibraltar": "🇬🇮", "Greece": "🇬🇷", "Greenland": "🇬🇱", "Grenada": "🇬🇩", "Guadeloupe": "🇬🇵", "Guam": "🇬🇺",
    "Guatemala": "🇬🇹", "Guinea": "🇬🇳", "Guinea-Bissau": "🇬🇼", "Guyana": "🇬🇾", "Haiti": "🇭🇹", "Honduras": "🇭🇳", "Hong Kong": "🇭🇰", "Hungary": "🇭🇺",
    "Iceland": "🇮🇸", "India": "🇮🇳", "Indonesia": "🇮🇩", "Iran": "🇮🇷", "Iraq": "🇮🇶", "Ireland": "🇮🇪", "Israel": "🇮🇱", "Italy": "🇮🇹",
    "Ivory Coast": "🇨🇮", "Jamaica": "🇯🇲", "Japan": "🇯🇵", "Jordan": "🇯🇴", "Kazakhstan": "🇰🇿", "Kenya": "🇰🇪", "Kiribati": "🇰🇮", "Kosovo": "🇽🇰",
    "Kuwait": "🇰🇼", "Kyrgyzstan": "🇰🇬", "Laos": "🇱🇦", "Latvia": "🇱🇻", "Lebanon": "🇱🇧", "Lesotho": "🇱🇸", "Liberia": "🇱🇷", "Libya": "🇱🇾",
    "Liechtenstein": "🇱🇮", "Lithuania": "🇱🇹", "Luxembourg": "🇱🇺", "Macau": "🇲🇴", "Macedonia": "🇲🇰", "Madagascar": "🇲🇬", "Malawi": "🇲🇼", "Malaysia": "🇲🇾",
    "Maldives": "🇲🇻", "Mali": "🇲🇱", "Malta": "🇲🇹", "Marshall Islands": "🇲🇭", "Martinique": "🇲🇶", "Mauritania": "🇲🇷", "Mauritius": "🇲🇺", "Mexico": "🇲🇽",
    "Micronesia": "🇫🇲", "Moldova": "🇲🇩", "Monaco": "🇲🇨", "Mongolia": "🇲🇳", "Montenegro": "🇲🇪", "Montserrat": "🇲🇸", "Morocco": "🇲🇦", "Mozambique": "🇲🇿",
    "Myanmar": "🇲🇲", "Namibia": "🇳🇦", "Nauru": "🇳🇷", "Nepal": "🇳🇵", "Netherlands": "🇳🇱", "New Caledonia": "🇳🇨", "New Zealand": "🇳🇿", "Nicaragua": "🇳🇮",
    "Niger": "🇳🇪", "Nigeria": "🇳🇬", "Niue": "🇳🇺", "North Korea": "🇰🇵", "Norway": "🇳🇴", "Oman": "🇴🇲", "Pakistan": "🇵🇰", "Palau": "🇵🇼",
    "Palestine": "🇵🇸", "Panama": "🇵🇦", "Papua New Guinea": "🇵🇬", "Paraguay": "🇵🇾", "Peru": "🇵🇪", "Philippines": "🇵🇭", "Poland": "🇵🇱", "Portugal": "🇵🇹",
    "Puerto Rico": "🇵🇷", "Qatar": "🇶🇦", "Reunion": "🇷🇪", "Romania": "🇷🇴", "Russia": "🇷🇺", "Rwanda": "🇷🇼", "St. Kitts and Nevis": "🇰🇳", "St. Lucia": "🇱🇨",
    "St. Vincent": "🇻🇨", "Samoa": "🇼🇸", "San Marino": "🇸🇲", "Sao Tome and Principe": "🇸🇹", "Saudi Arabia": "🇸🇦", "Senegal": "🇸🇳", "Serbia": "🇷🇸", "Seychelles": "🇸🇨",
    "Sierra Leone": "🇸🇱", "Singapore": "🇸🇬", "Slovakia": "🇸🇰", "Slovenia": "🇸🇮", "Solomon Islands": "🇸🇧", "Somalia": "🇸🇴", "South Africa": "🇿🇦", "South Korea": "🇰🇷",
    "South Sudan": "🇸🇸", "Spain": "🇪🇸", "Sri Lanka": "🇱🇰", "Sudan": "🇸🇩", "Suriname": "🇸🇷", "Swaziland": "🇸🇿", "Sweden": "🇸🇪", "Switzerland": "🇨🇭",
    "Syria": "🇸🇾", "Taiwan": "🇹🇼", "Tajikistan": "🇹🇯", "Tanzania": "🇹🇿", "Thailand": "🇹🇭", "Timor-Leste": "🇹🇱", "Togo": "🇹🇬", "Tonga": "🇹🇴",
    "Trinidad and Tobago": "🇹🇹", "Tunisia": "🇹🇳", "Turkey": "🇹🇷", "Turkmenistan": "🇹🇲", "Turks and Caicos": "🇹🇨", "Tuvalu": "🇹🇻", "Uganda": "🇺🇬", "Ukraine": "🇺🇦",
    "UAE": "🇦🇪", "United Kingdom": "🇬🇧", "USA": "🇺🇸", "USA/Canada": "🇺🇸", "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿", "Vanuatu": "🇻🇺", "Venezuela": "🇻🇪",
    "Vietnam": "🇻🇳", "Virgin Islands (US)": "🇻🇮", "Wallis and Futuna": "🇼🇫", "Yemen": "🇾🇪", "Zambia": "🇿🇲", "Zimbabwe": "🇿🇼"
}

SERVICE_EMOJIS = {
    "Telegram": "📩", "WhatsApp": "🟢", "Facebook": "📘", "Instagram": "📸", 
    "Google": "🔍", "Twitter": "🐦", "TikTok": "🎵", "Unknown": "❓"
}

def get_country_from_phone(phone):
    prefixes = {
        '93': 'Afghanistan', '355': 'Albania', '213': 'Algeria', '1684': 'American Samoa', '376': 'Andorra', '244': 'Angola', '1264': 'Anguilla',
        '1268': 'Antigua and Barbuda', '54': 'Argentina', '374': 'Armenia', '297': 'Aruba', '61': 'Australia', '43': 'Austria', '994': 'Azerbaijan',
        '1242': 'Bahamas', '973': 'Bahrain', '880': 'Bangladesh', '1246': 'Barbados', '375': 'Belarus', '32': 'Belgium', '501': 'Belize',
        '229': 'Benin', '1441': 'Bermuda', '975': 'Bhutan', '591': 'Bolivia', '387': 'Bosnia', '267': 'Botswana', '55': 'Brazil', '673': 'Brunei',
        '359': 'Bulgaria', '226': 'Burkina Faso', '257': 'Burundi', '855': 'Cambodia', '237': 'Cameroon', '1': 'USA/Canada', '238': 'Cape Verde',
        '1345': 'Cayman Islands', '236': 'CAR', '235': 'Chad', '56': 'Chile', '86': 'China', '57': 'Colombia', '269': 'Comoros', '242': 'Congo',
        '243': 'DR Congo', '682': 'Cook Islands', '506': 'Costa Rica', '385': 'Croatia', '53': 'Cuba', '357': 'Cyprus', '420': 'Czechia',
        '45': 'Denmark', '253': 'Djibouti', '1767': 'Dominica', '1809': 'Dominican Rep', '1829': 'Dominican Rep', '1849': 'Dominican Rep',
        '593': 'Ecuador', '20': 'Egypt', '503': 'El Salvador', '240': 'Equatorial Guinea', '291': 'Eritrea', '372': 'Estonia', '251': 'Ethiopia',
        '500': 'Falkland Islands', '298': 'Faroe Islands', '679': 'Fiji', '358': 'Finland', '33': 'France', '594': 'French Guiana', '689': 'French Polynesia',
        '241': 'Gabon', '220': 'Gambia', '995': 'Georgia', '49': 'Germany', '233': 'Ghana', '350': 'Gibraltar', '30': 'Greece', '299': 'Greenland',
        '1473': 'Grenada', '590': 'Guadeloupe', '1671': 'Guam', '502': 'Guatemala', '224': 'Guinea', '245': 'Guinea-Bissau', '592': 'Guyana',
        '509': 'Haiti', '504': 'Honduras', '852': 'Hong Kong', '36': 'Hungary', '354': 'Iceland', '91': 'India', '62': 'Indonesia', '98': 'Iran',
        '964': 'Iraq', '353': 'Ireland', '972': 'Israel', '39': 'Italy', '225': 'Ivory Coast', '1876': 'Jamaica', '81': 'Japan', '962': 'Jordan',
        '7': 'Russia', '254': 'Kenya', '686': 'Kiribati', '383': 'Kosovo', '965': 'Kuwait', '996': 'Kyrgyzstan', '856': 'Laos', '371': 'Latvia',
        '961': 'Lebanon', '266': 'Lesotho', '231': 'Liberia', '218': 'Libya', '423': 'Liechtenstein', '370': 'Lithuania', '352': 'Luxembourg',
        '853': 'Macau', '389': 'Macedonia', '261': 'Madagascar', '265': 'Malawi', '60': 'Malaysia', '960': 'Maldives', '223': 'Mali',
        '356': 'Malta', '692': 'Marshall Islands', '596': 'Martinique', '222': 'Mauritania', '230': 'Mauritius', '52': 'Mexico', '691': 'Micronesia',
        '373': 'Moldova', '377': 'Monaco', '976': 'Mongolia', '382': 'Montenegro', '1664': 'Montserrat', '212': 'Morocco', '258': 'Mozambique',
        '95': 'Myanmar', '264': 'Namibia', '674': 'Nauru', '977': 'Nepal', '31': 'Netherlands', '687': 'New Caledonia', '64': 'New Zealand',
        '505': 'Nicaragua', '227': 'Niger', '234': 'Nigeria', '683': 'Niue', '850': 'North Korea', '47': 'Norway', '968': 'Oman', '92': 'Pakistan',
        '680': 'Palau', '970': 'Palestine', '507': 'Panama', '675': 'Papua New Guinea', '595': 'Paraguay', '51': 'Peru', '63': 'Philippines',
        '48': 'Poland', '351': 'Portugal', '1787': 'Puerto Rico', '1939': 'Puerto Rico', '974': 'Qatar', '262': 'Reunion', '40': 'Romania',
        '7': 'Russia', '250': 'Rwanda', '1869': 'St. Kitts and Nevis', '1758': 'St. Lucia', '1784': 'St. Vincent', '685': 'Samoa', '378': 'San Marino',
        '239': 'Sao Tome and Principe', '966': 'Saudi Arabia', '221': 'Senegal', '381': 'Serbia', '248': 'Seychelles', '232': 'Sierra Leone',
        '65': 'Singapore', '421': 'Slovakia', '386': 'Slovenia', '677': 'Solomon Islands', '252': 'Somalia', '27': 'South Africa', '82': 'South Korea',
        '211': 'South Sudan', '34': 'Spain', '94': 'Sri Lanka', '249': 'Sudan', '597': 'Suriname', '268': 'Swaziland', '46': 'Sweden',
        '41': 'Switzerland', '963': 'Syria', '886': 'Taiwan', '992': 'Tajikistan', '255': 'Tanzania', '66': 'Thailand', '670': 'Timor-Leste',
        '228': 'Togo', '676': 'Tonga', '1868': 'Trinidad and Tobago', '216': 'Tunisia', '90': 'Turkey', '993': 'Turkmenistan', '1649': 'Turks and Caicos',
        '688': 'Tuvalu', '256': 'Uganda', '380': 'Ukraine', '971': 'UAE', '44': 'United Kingdom', '1': 'USA', '598': 'Uruguay', '998': 'Uzbekistan',
        '678': 'Vanuatu', '39': 'Vatican City', '58': 'Venezuela', '84': 'Vietnam', '1340': 'Virgin Islands (US)', '681': 'Wallis and Futuna',
        '967': 'Yemen', '260': 'Zambia', '263': 'Zimbabwe'
    }
    sorted_p = sorted(prefixes.items(), key=lambda x: len(x[0]), reverse=True)
    for p, c in sorted_p:
        if phone.startswith(p): return c
    
    # Fallback for prefix 1 which is common and sometimes missed
    if phone.startswith('1'): return 'USA/Canada'
    
    return "Unknown"

driver = None
chrome_process = None
last_refresh_time = time.time()

# --- UI Helpers ---
def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📱 GET NUMBER", callback_data='get_number')],
        [InlineKeyboardButton("📊 STATISTICS", callback_data='stats'),
         InlineKeyboardButton("👤 ACCOUNT", callback_data='account')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 BROADCAST", callback_data='admin_broadcast'),
         InlineKeyboardButton("➕ ADD STOCK (.txt)", callback_data='admin_add_stock')],
        [InlineKeyboardButton("📊 FULL STATS", callback_data='stats'),
         InlineKeyboardButton("🗑️ CLEAR STOCK", callback_data='admin_clear_stock')],
        [InlineKeyboardButton("🔄 SWITCH TO USER MODE", callback_data='switch_user_mode')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_force_join_keyboard():
    keyboard = []
    for idx, group in enumerate(FORCE_JOIN_GROUPS, 1):
        keyboard.append([InlineKeyboardButton(f"Join Group {idx}", url=group["link"])])
    keyboard.append([InlineKeyboardButton("✅ VERIFY", callback_data='verify_join')])
    return InlineKeyboardMarkup(keyboard)

# --- Bot Logic ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🤖 *WELCOME TO BGGR SMS*"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=get_main_menu_keyboard(), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(), parse_mode='MarkdownV2')

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        r"👑 *OWNER PANEL*" + "\n\n"
        r"Welcome Boss\! Manage your bot below\." + "\n"
        r"• Send `.txt` file to add stock\." + "\n"
        r"• Use `/broadcast <msg>` for alerts\."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=get_admin_menu_keyboard(), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(text, reply_markup=get_admin_menu_keyboard(), parse_mode='MarkdownV2')

async def check_membership(user_id, bot):
    try:
        if str(user_id) in ADMIN_CHAT_IDS: return True
        for group in FORCE_JOIN_GROUPS:
            member = await bot.get_chat_member(chat_id=group["id"], user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        return True
    except: return False

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_CHAT_IDS: return
    
    msg_text = " ".join(context.args)
    if not msg_text:
        await update.message.reply_text("❌ Usage: `/broadcast <message>`", parse_mode='MarkdownV2')
        return
        
    users = db.get_all_users()
    count = 0
    for cid in users:
        try:
            await context.bot.send_message(chat_id=cid, text=escape_markdown(msg_text), parse_mode='MarkdownV2')
            count += 1
        except: pass
    
    await update.message.reply_text(f"✅ Broadcast sent to `{count}` users\\.", parse_mode='MarkdownV2')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    if str(user.id) in ADMIN_CHAT_IDS:
        await show_admin_menu(update, context)
    elif await check_membership(user.id, context.bot):
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("⚠️ *Access Denied*\nJoin our channels first:", reply_markup=get_force_join_keyboard(), parse_mode='MarkdownV2')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == 'back_home':
        if str(user_id) in ADMIN_CHAT_IDS: await show_admin_menu(update, context)
        else: await show_main_menu(update, context)
        return

    if data == 'verify_join':
        if await check_membership(user_id, context.bot): await show_main_menu(update, context)
        else: await query.answer("❌ Join all groups first!", show_alert=True)
    
    elif data == 'switch_user_mode':
        await show_main_menu(update, context)

    elif data == 'admin_broadcast':
        user_count = db.get_total_users_count()
        text = (
            f"📢 *BROADCAST SYSTEM*\n\n"
            f"Total Users: `{user_count}`\n\n"
            r"To send a broadcast, type\:" + "\n"
            r"`/broadcast <your message>`"
        )
        kb = [[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

    elif data == 'stats':
        countries = db.get_available_countries()
        text = "📊 *AVAILABLE STOCK*\n\n"
        if not countries: text += "❌ Out of Stock"
        else:
            for country, count in countries:
                flag = COUNTRY_FLAGS_MAP.get(country.strip().title(), "🏳️")
                text += f"{flag} {escape_markdown(country)}: `{count}`\n"
            text += f"\n📈 Total: `{sum(c[1] for c in countries)}`"
        kb = [[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

    elif data == 'get_number':
        countries = db.get_available_countries()
        if not countries:
            await query.edit_message_text("❌ Out of Stock", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]))
            return
        
        text = "📱 *SELECT COUNTRY:*"
        keyboard = []
        for country, count in countries:
            flag = COUNTRY_FLAGS_MAP.get(country.strip().title(), "🏳️")
            keyboard.append([InlineKeyboardButton(f"{flag} {country} ({count})", callback_data=f"sel_{country}")])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data='back_home')])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')

    elif data.startswith('sel_'):
        country = data.split('_', 1)[1]
        new_numbers = db.allocate_numbers(user_id, count=2, country=country)
        if not new_numbers:
            await query.answer("❌ Stock ran out for this country!", show_alert=True)
            await query.edit_message_text("Try another country.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data='get_number')]]))
            return
        
        msg = f"🛒 *YOUR {escape_markdown(country).upper()} NUMBERS:*\n\n"
        flag = COUNTRY_FLAGS_MAP.get(country, "🏳️")
        for num, _ in new_numbers:
            msg += f"{flag} `{num}`\n"
        msg += "\n⏳ Waiting for SMS\\.\\.\\."
        
        kb = [[InlineKeyboardButton("🔄 CHANGE NUMBER", callback_data=f"sel_{country}")],
              [InlineKeyboardButton("🌍 CHANGE COUNTRY", callback_data='get_number')],
              [InlineKeyboardButton("🔙 BACK TO MENU", callback_data='back_home')],
              [InlineKeyboardButton("🔔 OTP VIEW", url="https://t.me/OTPBEGRSS")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

    elif data == 'admin_clear_stock':
        countries = db.get_available_countries()
        if not countries:
            await query.edit_message_text("❌ No stock available to clear\\.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]), parse_mode='MarkdownV2')
            return
        
        text = "🗑️ *SELECT COUNTRY TO CLEAR STOCK*\n\n_Note: This only deletes available numbers\\. User history is preserved\\._"
        keyboard = []
        for country, count in countries:
            flag = COUNTRY_FLAGS_MAP.get(country, "🏳️")
            keyboard.append([InlineKeyboardButton(f"{flag} {country} ({count})", callback_data=f"clear_conf_{country}")])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data='back_home')])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')

    elif data.startswith('clear_conf_'):
        country = data.split('_', 2)[2]
        text = f"🚨 *CONFIRMATION*\n\nAre you sure you want to delete ALL available numbers for *{escape_markdown(country)}*?\n\nThis cannot be undone\\!"
        kb = [[InlineKeyboardButton("✅ YES, DELETE", callback_data=f"clear_exe_{country}")],
              [InlineKeyboardButton("❌ NO, CANCEL", callback_data='admin_clear_stock')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

    elif data.startswith('clear_exe_'):
        country = data.split('_', 2)[2]
        deleted_count = db.delete_country_stock(country)
        text = f"✅ *SUCCESS*\n\nDeleted `{deleted_count}` available numbers for *{escape_markdown(country)}*\\."
        kb = [[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

    elif data == 'account':
        stats = db.get_user_stats(user_id)
        text = "👤 *YOUR ACCOUNT STATS*\n\n"
        if not stats:
            text += "You haven't used any numbers yet\\."
        else:
            text += "🔢 *Numbers used per country:*\n"
            for country, count in stats:
                flag = COUNTRY_FLAGS_MAP.get(country.strip().title(), "🏳️")
                text += f"{flag} {escape_markdown(country)}: `{count}`\n"
            text += f"\n📊 *Total Usage:* `{sum(c[1] for c in stats)}`"
            
        kb = [[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

    elif data.startswith('confirm_stock_'):
        # confirm_stock_yes OR confirm_stock_no
        action = data.split('_')[2]
        pending_stock = context.user_data.get('pending_stock')
        
        if not pending_stock:
            await query.edit_message_text("❌ Session expired or no pending stock found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]))
            return

        if action == 'yes':
            count = db.add_numbers_bulk(pending_stock)
            await query.edit_message_text(f"✅ *DONE*\n\nSuccessfully added `{count}` new numbers to the database\\.", parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]))
        else:
            await query.edit_message_text("❌ Operation Cancelled\\.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data='back_home')]]), parse_mode='MarkdownV2')
        
        # Clear data
        context.user_data.pop('pending_stock', None)


# --- Upload Stock ---
async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_CHAT_IDS: return
    doc = update.message.document
    if not doc.file_name.endswith('.txt'): return

    file = await doc.get_file()
    file_path = f"downloads/{doc.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await file.download_to_drive(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = []
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('|')
            phone = parts[0].strip()
            if len(parts) > 1: country = parts[1].strip()
            else: country = get_country_from_phone(phone)
            data.append((phone, country))
    
    os.remove(file_path)

    # CHECK DUPLICATES
    unique_new, duplicates_count = db.check_stock_duplicates(data)
    
    if duplicates_count == 0:
        # No duplicates, add direct
        count = db.add_numbers_bulk(unique_new)
        await update.message.reply_text(f"✅ Added {count} numbers from file\\.\nExample: {data[0][0]} \\-\\> {data[0][1]}", parse_mode='MarkdownV2')
    else:
        # Ask for confirmation
        context.user_data['pending_stock'] = unique_new
        text = (
            f"⚠️ *DUPLICATE WARNING*\n\n"
            f"Found `{duplicates_count}` duplicate numbers already in bot\\.\n"
            f"New numbers to add: `{len(unique_new)}`\n\n"
            f"Do you want to proceed adding ONLY the {len(unique_new)} new numbers?"
        )
        kb = [
            [InlineKeyboardButton(f"✅ YES, ADD {len(unique_new)} NEW", callback_data='confirm_stock_yes')],
            [InlineKeyboardButton("❌ CANCEL", callback_data='confirm_stock_no')]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')

async def handle_text_stock_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_CHAT_IDS: return
    
    msg_text = update.message.text
    if not msg_text: return
    
    # Simple heuristic: if the message starts with a digit and has more than 5 lines
    lines = [l.strip() for l in msg_text.split('\n') if l.strip()]
    if not lines: return
    
    # Check if first 3 lines are mostly digits (to avoid catching /commands or normal text)
    is_numbers = True
    for l in lines[:3]:
        if not re.search(r'\d{6,}', l):
            is_numbers = False
            break
    
    if not is_numbers: return
    
    data = []
    processed_count = 0
    for line in lines:
        # Extract digits
        phone = re.sub(r'\D', '', line)
        if not phone: continue
        
        country = get_country_from_phone(phone)
        data.append((phone, country))
        processed_count += 1
        
    if not data: return
    
    # CHECK DUPLICATES
    unique_new, duplicates_count = db.check_stock_duplicates(data)

    if duplicates_count > 0:
        # Ask for confirmation
        context.user_data['pending_stock'] = unique_new
        text = (
            f"⚠️ *DUPLICATE WARNING*\n\n"
            f"Found `{duplicates_count}` duplicate numbers already in bot\\.\n"
            f"New numbers to add: `{len(unique_new)}`\n\n"
            f"Do you want to proceed adding ONLY the {len(unique_new)} new numbers?"
        )
        kb = [
            [InlineKeyboardButton(f"✅ YES, ADD {len(unique_new)} NEW", callback_data='confirm_stock_yes')],
            [InlineKeyboardButton("❌ CANCEL", callback_data='confirm_stock_no')]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='MarkdownV2')
        return

    # Add to DB direct if no duplicates
    count = db.add_numbers_bulk(unique_new)
    
    # Generate .txt file to send back
    import io
    output = io.BytesIO()
    file_content = ""
    for p, c in data:
        # Simplified output: Just the number, no country
        file_content += f"{p}\n"
    
    output.write(file_content.encode('utf-8'))
    output.seek(0)
    
    # Determine country for filename (use first entry)
    country_name = "STOCK"
    if data:
        country_name = data[0][1].upper().replace(" ", "_")

    date_str = datetime.now().strftime('%Y%m%d')
    filename = f"{country_name}_{date_str}.txt"

    await update.message.reply_text(f"✅ Processed {processed_count} numbers from text\\.\nAdded `{count}` new numbers to database\\.", parse_mode='MarkdownV2')
    
    # Send the file back
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=output,
        filename=filename,
        caption="📄 *Generated Stock File*" ,
        parse_mode='MarkdownV2'
    )

# --- Selenium ---
def find_chrome_executable():
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    # Check enviroment variable (Docker support)
    if os.environ.get("CHROME_PATH"):
        possible_paths.insert(0, os.environ.get("CHROME_PATH"))
        
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Fallback for Linux/Docker
    if platform.system() == 'Linux':
        try:
             return subprocess.check_output(["which", "google-chrome"]).decode().strip()
        except:
             return "/usr/bin/google-chrome"
             
    return None

def verify_chrome_running():
    # Simple check if port 9222 is active or if we can connect
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 9222))
    sock.close()
    return result == 0

def init_driver():
    global driver, chrome_process
    
    if driver is not None:
        try:
            _ = driver.current_url
            return driver
        except:
            print("⚠️ Driver not responding, restarting...")
            driver = None
    
    # 1. Launch Chrome if not running on port 9222
    if not verify_chrome_running():
        chrome_path = find_chrome_executable()
        if not chrome_path:
            print("❌ Chrome executable not found!")
            return None
            
        profile_path = os.path.abspath('chrome_debug_profile')
        cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile_path}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        
        # Add necessary flags for docker/xvfb info
        if platform.system() == 'Linux':
             cmd.extend(["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"])
        
        print(f"🚀 Launching Chrome: {chrome_path}")
        try:
            chrome_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5) # Wait for startup
        except Exception as e:
            print(f"❌ Failed to launch Chrome: {e}")
            return None

    # 2. Attach Driver
    if driver is None:
        try:
            print("🌐 Attaching to Chrome (127.0.0.1:9222)...")
            options = uc.ChromeOptions()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            
            driver = uc.Chrome(options=options, version_main=114) # Check version if needed
            print("[+] Chrome Attached!")
        except Exception as e: 
            print(f"[x] Attachment Failed: {e}")
            return None
            
    return driver

def perform_login(driver):
    try:
        print("[*] Attempting Auto-Login...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        # Check if we are already redirected to dashboard or something
        if "login" not in driver.current_url:
            print("✅ Already logged in (redirected).")
            return
            
        # Locate elements - Adjust selectors based on actual page
        # Assuming standard names/types for email/pass
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email'], input[type='email']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password'], input[type='password']")
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        email_input.clear()
        email_input.send_keys(IVAS_EMAIL)
        password_input.clear()
        password_input.send_keys(IVAS_PASSWORD)
        time.sleep(1)
        submit_btn.click()
        
        # Wait for login to complete (url change or detection of dashboard element)
        time.sleep(5)
        if "login" not in driver.current_url:
            print("✅ Login Successful!")
        else:
            print("❌ Login Check Failed (Still on login url)")
            
    except Exception as e:
        print(f"❌ Login Error: {e}")

def fetch_sms_selenium():
    global driver, last_refresh_time
    msgs = []
    try:
        # Auto-Refresh Every 1 Hour
        if time.time() - last_refresh_time > 3600:
            try:
                # Silent auto-refresh
                driver.refresh()
                time.sleep(5)
                last_refresh_time = time.time()
            except: 
                pass # Silently ignore errors

        # Smart Navigation: Only navigate if we are not on the Live SMS page
        target_url = "https://www.ivasms.com/portal/live/my_sms"
        
        current_url = driver.current_url
        
        # Auto-Login Check
        if "login" in current_url or "signin" in current_url:
            perform_login(driver)
            current_url = driver.current_url # update after login
        
        if target_url not in current_url:
            print(f"🚀 Navigating to {target_url}...")
            driver.get(target_url)
            time.sleep(5) # Wait for table to load
            
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tbody = soup.find('tbody', id='LiveTestSMS')
        if not tbody: return [] 
        
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 5: continue
            c_tag = cells[0].find('a')
            country = re.sub(r'\s+\d+$', '', c_tag.text.strip()) if c_tag else "Unknown"
            phone_text = cells[0].find('p', class_='CopyText').text.strip()
            phone = re.sub(r'\D', '', phone_text) # Keep only digits for matching
            service = cells[1].text.strip()
            text = cells[4].get_text(separator=' ').strip()
            
            # Improved Code Extraction
            code = "N/A"
            # Look for various patterns: G-123456, 123-456, 123 456, or 4-10 digits
            
            # 1. Google G-XXXXXX
            google_match = re.search(r'(G-\d{6})', text)
            # 2. Hyphenated or Spaced codes like 123-456 or 123 456
            hyphen_match = re.search(r'(\d{3}[\-\s]\d{3})', text)
            # 3. Keyword based: "code is 123456"
            keyword_match = re.search(r'(?:code|is|pin|passcode|otp|verification)\s*(?:is|:)?\s*(\d{4,10})', text, re.IGNORECASE)
            # 4. Any 4-10 digit number
            any_match = re.search(r'(\d{4,10})', text)
            
            if google_match:
                code = google_match.group(1)
            elif hyphen_match:
                code = hyphen_match.group(1)
            elif keyword_match:
                code = keyword_match.group(1)
            elif any_match:
                code = any_match.group(1)
            
            # Generate a truly unique ID based on number and full message text
            # This allows multiple OTPs for the same number to be sent
            unique_id = hashlib.md5(f"{phone}-{text}".encode('utf-8')).hexdigest()
            
            msgs.append({
                "id": unique_id, 
                "number": phone, 
                "country": country, 
                "service": service, 
                "code": code, 
                "text": text
            })
    except Exception as e:
        print(f"Error in fetch_sms: {e}")
        pass
    return msgs

processed_ids = set()

async def check_sms_job(context: ContextTypes.DEFAULT_TYPE):
    global processed_ids
    print(f"[{datetime.now()}] Scanning...")
    driver = init_driver()
    if not driver: return
    msgs = fetch_sms_selenium()
    for msg in reversed(msgs):
        if msg['id'] in processed_ids: continue
        processed_ids.add(msg['id'])
        
        # ✅ Increment OTP Count (So successful numbers get deleted later)
        db.increment_otp_count(msg['number'])
        
        owner_id = db.find_owner_of_number(msg['number'])
        
        # Normalize country for flag lookup
        country_name = msg['country'].strip()
        flag = "🏳️"
        # Try exact, then title, then upper
        for k in [country_name, country_name.title(), country_name.upper()]:
            if k in COUNTRY_FLAGS_MAP:
                flag = COUNTRY_FLAGS_MAP[k]
                break
        
        # Logic: 
        # 1. To Owner: Always FULL number
        # 2. To Group: MASKED number (xxxx...1234)
        
        full_text = (f"🔔 *OTP RECEIVED*\n"
                f"🌍 {flag} *{escape_markdown(msg['country'])}*\n"
                f"📱 {flag} `{msg['number']}`\n"
                f"🔑 `{msg['code']}`\n"
                f"🏆 {SERVICE_EMOJIS.get(msg['service'], '❓')} {escape_markdown(msg['service'])}\n"
                f"💬 `{escape_markdown(msg['text'])}`")
        
        # Masking Logic
        num = msg['number']
        masked_num = num
        if len(num) > 4:
            masked_num = "x" * (len(num) - 4) + num[-4:]
            
        group_text = (f"🔔 *OTP RECEIVED*\n"
                f"🌍 {flag} *{escape_markdown(msg['country'])}*\n"
                f"📱 {flag} `{masked_num}`\n"
                f"🔑 `{msg['code']}`\n"
                f"🏆 {SERVICE_EMOJIS.get(msg['service'], '❓')} {escape_markdown(msg['service'])}\n"
                f"💬 `{escape_markdown(msg['text'])}`")
        
        if owner_id:
            try: await context.bot.send_message(owner_id, full_text, parse_mode='MarkdownV2')
            except: pass
        else:
            # Debug for Admins: Alert if OTP is found but no owner in DB
            # for admin_id in ADMIN_CHAT_IDS:
            #     try: await context.bot.send_message(admin_id, f"⚠️ *UNOWNED OTP*\n\n{full_text}", parse_mode='MarkdownV2')
            #     except: pass
            pass

        try:
            m = await context.bot.send_message(OTP_GROUP_ID, group_text, parse_mode='MarkdownV2')
            context.job_queue.run_once(delete_msg, 300, data={'chat_id': OTP_GROUP_ID, 'msg_id': m.message_id})
        except Exception:
            # traceback.print_exc()
            pass

async def delete_msg(context: ContextTypes.DEFAULT_TYPE):
    try:
        data = context.job.data
        await context.bot.delete_message(chat_id=data['chat_id'], message_id=data['msg_id'])
    except Exception:
        pass # Silently fail if message already deleted

async def delete_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass

def main():
    if not YOUR_BOT_TOKEN:
         print("❌ Error: BOT_TOKEN not found in .env")
         return

    app = Application.builder().token(YOUR_BOT_TOKEN).read_timeout(30).connect_timeout(30).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_stock_upload))
    # Combined filter for New Members AND Left Members
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_join))
    
    app.job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS)
    print("BOT BGGR SMS STARTED")
    print("IMPORTANT: Please send /start to the bot to refresh menu!")
    app.run_polling()

if __name__ == "__main__":
    main()
