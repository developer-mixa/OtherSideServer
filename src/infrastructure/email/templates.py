"""Rendering of transactional email bodies.

Email clients are stuck a decade behind browsers: layout is tables, every style is
inline, and anything external (fonts, images, stylesheets) is blocked or stripped.
Both a plain-text and an HTML part are produced so text-only clients still get a
readable message.
"""

from __future__ import annotations

from html import escape

# Mirrors the site palette in OtherSideFrontend/src/app/globals.css.
_BACKGROUND = "#050505"
_SURFACE = "#0d0d0d"
_CODE_SURFACE = "#141414"
_BORDER = "#242424"
_FOREGROUND = "#f5f5f5"
_MUTED_FOREGROUND = "#a3a3a3"
_ACCENT = "#c9a962"

# Cormorant/Inter are webfonts the client cannot load — fall back the same way the site does.
_SERIF = "Georgia, 'Times New Roman', serif"
_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

VERIFICATION_SUBJECT = "Код подтверждения почты OtherSide"


def plural_minutes(count: int) -> str:
    """Russian plural form for 'минута' — '1 минуту', '3 минуты', '15 минут'."""
    if count % 100 in range(11, 15):
        return "минут"
    last = count % 10
    if last == 1:
        return "минуту"
    if last in (2, 3, 4):
        return "минуты"
    return "минут"


def render_verification_email(*, code: str, ttl_minutes: int, site_url: str) -> tuple[str, str]:
    """Return the (plain text, HTML) bodies for a verification code email."""
    validity = f"{ttl_minutes} {plural_minutes(ttl_minutes)}"

    text = (
        f"Ваш код подтверждения: {code}\n\n"
        f"Код действителен {validity}. Если вы не регистрировались "
        "на OtherSide, просто проигнорируйте это письмо.\n\n"
        f"{site_url}"
    )

    safe_code = escape(code)
    safe_site = escape(site_url, quote=True)
    # Spaced-out digits read as a code rather than a number, and stop clients from
    # linkifying it as a phone number.
    spaced_code = escape(" ".join(code))

    html = f"""\
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>{escape(VERIFICATION_SUBJECT)}</title>
</head>
<body style="margin:0; padding:0; background-color:{_BACKGROUND}; color:{_FOREGROUND};">
<div style="display:none; max-height:0; overflow:hidden; opacity:0;">
Ваш код подтверждения OtherSide: {safe_code}
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       bgcolor="{_BACKGROUND}" style="background-color:{_BACKGROUND};">
  <tr>
    <td align="center" style="padding:40px 16px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0"
             style="width:560px; max-width:100%; background-color:{_SURFACE};
                    border:1px solid {_BORDER}; border-radius:16px;">
        <tr>
          <td align="center" style="padding:40px 40px 8px 40px;">
            <span style="font-family:{_SANS}; font-size:12px; letter-spacing:5px;
                         text-transform:uppercase; color:{_MUTED_FOREGROUND};">OtherSide</span>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:16px 40px 0 40px;">
            <h1 style="margin:0; font-family:{_SERIF}; font-size:30px; font-weight:400;
                       line-height:1.25; color:{_FOREGROUND};">Подтверждение почты</h1>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:16px 40px 0 40px;">
            <p style="margin:0; font-family:{_SANS}; font-size:15px; line-height:1.6;
                      color:{_MUTED_FOREGROUND};">
              Введите этот код на сайте, чтобы завершить регистрацию.
            </p>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:28px 40px 0 40px;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0"
                   style="background-color:{_CODE_SURFACE}; border:1px solid {_BORDER};
                          border-radius:12px;">
              <tr>
                <td align="center" style="padding:22px 32px; font-family:{_SANS};
                           font-size:34px; font-weight:600; letter-spacing:8px;
                           color:{_ACCENT}; white-space:nowrap;">{spaced_code}</td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:18px 40px 0 40px;">
            <p style="margin:0; font-family:{_SANS}; font-size:13px; line-height:1.6;
                      color:{_MUTED_FOREGROUND};">
              Код действителен {escape(validity)}.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 40px 0 40px;">
            <div style="height:1px; background-color:{_BORDER}; line-height:1px;
                        font-size:0;">&nbsp;</div>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:20px 40px 36px 40px;">
            <p style="margin:0 0 10px 0; font-family:{_SANS}; font-size:12px; line-height:1.6;
                      color:{_MUTED_FOREGROUND};">
              Если вы не регистрировались на OtherSide, просто проигнорируйте это письмо.
            </p>
            <a href="{safe_site}" style="font-family:{_SANS}; font-size:12px;
               color:{_MUTED_FOREGROUND}; text-decoration:none;">{safe_site}</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""
    return text, html
