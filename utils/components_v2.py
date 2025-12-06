import discord

class Button:
    def __init__(self, label, custom_id):
        self.label = label
        self.custom_id = custom_id


class SelectOption:
    def __init__(self, label, value=None):
        self.label = label
        self.value = value or label


class Select:
    def __init__(self, placeholder, custom_id, options):
        self.placeholder = placeholder
        self.custom_id = custom_id
        self.options = options


class Section:
    def __init__(self, label, description="", buttons=None, selects=None):
        self.label = label
        self.description = description
        self.buttons = buttons or []
        self.selects = selects or []


class MessageBuilder:
    def __init__(self, title=""):
        self.title = title
        self.sections = []

    def add_section(self, section: Section):
        self.sections.append(section)

    def build(self):
        embeds = []
        views = []

        for sec in self.sections:
            embed = discord.Embed(
                title=sec.label,
                description=sec.description
            )
            embeds.append(embed)

            view = discord.ui.View(timeout=None)

            for b in sec.buttons:
                btn = discord.ui.Button(
                    label=b.label,
                    custom_id=b.custom_id
                )
                # callback を設定しない → 衝突しない
                view.add_item(btn)

            for s in sec.selects:
                sel = discord.ui.Select(
                    placeholder=s.placeholder,
                    options=[
                        discord.SelectOption(label=o.label, value=o.value)
                        for o in s.options
                    ],
                    custom_id=s.custom_id
                )
                # callback を設定しない → 衝突しない
                view.add_item(sel)

            views.append(view)

        return embeds, views
