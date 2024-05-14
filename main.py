from bot import Bot
from quart import Quart, request, render_template, jsonify
import discord

from creds import Auth, redirect_uri
from util.url import Url

endpoint = Url(redirect_uri).endpoint

app = Quart(__name__)
bot = Bot(app=app)

@app.route(endpoint)
async def callback():
    code = request.args.get("code")
    if not code:
        return await render_template("index.html", text="'code' parameter missing")
    
    guild_id = request.args.get("state")
    if not guild_id:
        return await render_template("index.html", text="'state' parameter missing")
    
    if not guild_id.isdigit():
        return await render_template("index.html", text="Invalid 'state' parameter provided")
    
    guild_id = int(guild_id)
    
    data = await Auth.get_access_token(code, bot.session)
    access_token = data.get("access_token")

    if not access_token:
        return await render_template("index.html", text="Invalid 'code' parameter provided")
    
    refresh_token = data["refresh_token"]

    user_info = await Auth.get_user_info(access_token, bot.session)
    user_id = int(user_info["id"])

    guild_object = bot.get_guild(guild_id)
    if not guild_object:
        return await render_template("index.html", text="Bot not in Server.")
    
    member = guild_object.get_member(user_id)

    guild_data = await bot.get_guild_data(guild_id)
    if guild_data == {}:
        return await render_template("index.html", text="Error fetching guild data.")
    
    role_id = guild_data["guild_verification_role"]
    role = guild_object.get_role(role_id)
    if not role:
        return await render_template("index.html", text="Role not found in server.")
    
    await member.add_roles(role)

    logs_channel = guild_object.get_channel(guild_data["logs_channel"])
    if logs_channel:
        embed = bot.embed(f"{member.mention} has authorized.", "Authorization Log", discord.Color.brand_green())
        await logs_channel.send(embed=embed)

    await bot.update_user(user_id, refresh_token)

    return await render_template("index.html", text="Thank you for verifying. You may now close this tab.")

@app.route("/status")
async def status():
    return jsonify({"status": "OK"})

@app.route("/guilds")
async def guilds():
    data = []
    guild_data = bot.collection.find({})
    for guild in guild_data:
        guild_id = guild["guild_id"]
        guild_name = guild["guild_name"]
        data.append(f"{guild_name} - {guild_id}")
        
    return jsonify(data)

@app.route("/<string:log>")
async def view(log: str):
    try:
        with open(f"./pull_logs/{log}", "r") as f:
            logs = f.readlines()

    except FileNotFoundError:
        return await render_template("index.html", text="Log not found.")
    
    return await render_template("logs.html", text=logs)

bot.run()