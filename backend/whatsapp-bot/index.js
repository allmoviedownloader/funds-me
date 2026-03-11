const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
require('dotenv').config({ path: '../.env' });

// Configuration
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const SUPABASE_HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json'
};

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './sessions'
    }),
    puppeteer: {
        args: ['--no-sandbox']
    }
});

// --- Supabase Logic ---

async function getFundsByQuery(query) {
    try {
        const url = `${SUPABASE_URL}/rest/v1/funds?or=(category.ilike.%${query}%,funding_stage.ilike.%${query}%)&limit=3&order=created_at.desc`;
        const res = await axios.get(url, { headers: SUPABASE_HEADERS });
        return res.data;
    } catch (error) {
        console.error('Error fetching funds:', error.message);
        return [];
    }
}

function formatReply(funds, category) {
    if (!funds || funds.length === 0) {
        return `Sorry! Mujhe abhi ${category} ke liye koi active funds nahi mile. Check again tomorrow!`;
    }
    
    let reply = `🚀 *Latest ${category} Opportunities:*\n\n`;
    funds.forEach(f => {
        reply += `🏢 *${f.company_name}*\n`;
        reply += `💰 ${f.amount_offered}\n`;
        reply += `🔗 Link: ${f.apply_link}\n\n`;
    });
    
    reply += "Aur jaanne ke liye *'MENU'* likhen.";
    return reply;
}

// --- WhatsApp Logic ---

client.on('qr', (qr) => {
    console.log('--- SCAN QR CODE BELOW ---');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ WhatsApp Bot is ready and logged in!');
});

client.on('message', async msg => {
    const text = msg.body.toLowerCase();
    
    if (text === 'hi' || text === 'hello' || text === 'menu') {
        const welcome = "Swagat hai! 🙏 Kis type ki funding chahiye?\n\n1. *Govt* - Government Challenges\n2. *Seed* - Private Seed Funds\n3. *Idea* - Idea Stage Funds\n\nBass keyword reply karein (e.g. 'Govt').";
        await client.sendMessage(msg.from, welcome);
        return;
    }
    
    if (text.includes('govt')) {
        const data = await getFundsByQuery('Government');
        await client.sendMessage(msg.from, formatReply(data, 'Government'));
    } else if (text.includes('seed')) {
        const data = await getFundsByQuery('Seed');
        await client.sendMessage(msg.from, formatReply(data, 'Seed'));
    } else if (text.includes('idea')) {
        const data = await getFundsByQuery('Idea');
        await client.sendMessage(msg.from, formatReply(data, 'Idea Stage'));
    }
});

client.initialize();
