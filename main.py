# main.py - Monitor de Noticias Ecuador
import os
import time
import requests
import feedparser
import hashlib
import json
from datetime import datetime
import telegram
import schedule
import threading

class EcuadorNewsMonitor:
    def __init__(self):
        # Variables de entorno Railway
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', 
'7731785599:AAFWO_-Dc6oUtvc5NCc1Ms2qiNZwc76T2KA')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '5075463133')
        
        # Verificar configuración
        if not self.bot_token or not self.chat_id:
            print("❌ Faltan variables de entorno")
            return
            
        self.bot = telegram.Bot(token=self.bot_token)
        
        # Keywords a monitorear
        self.keywords = [
            'CONAIE',
            'PLUSPETROL', 
            'SOLGOLD',
            'DUNDEE PRECIOUS METALS ECUADOR',
            'DUNDEE PRECIOUS METALS',
            'minería Ecuador',
            'pueblos indígenas Ecuador',
            'concesión minera Ecuador',
            'territorio ancestral'
        ]
        
        # Fuentes RSS
        self.sources = [
            'https://www.elcomercio.com/rss/',
            'https://www.eluniverso.com/rss/', 
            'https://www.primicias.ec/rss/',
            
'https://news.google.com/rss/search?q=Ecuador+minería&hl=es&gl=EC&ceid=EC:es',
            
'https://news.google.com/rss/search?q=CONAIE&hl=es&gl=EC&ceid=EC:es',
            
'https://news.google.com/rss/search?q=PLUSPETROL+Ecuador&hl=es&gl=EC&ceid=EC:es',
            
'https://news.google.com/rss/search?q=SOLGOLD&hl=es&gl=EC&ceid=EC:es',
            
'https://news.google.com/rss/search?q="DUNDEE+PRECIOUS+METALS"&hl=es&gl=EC&ceid=EC:es'
        ]
        
        # Archivo para evitar duplicados
        self.seen_file = 'seen_articles.json'
        self.seen_articles = self.load_seen_articles()
        
        print("✅ Monitor inicializado correctamente")
    
    def load_seen_articles(self):
        """Cargar artículos ya procesados"""
        try:
            with open(self.seen_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except:
            return set()
    
    def save_seen_articles(self):
        """Guardar artículos procesados"""
        try:
            with open(self.seen_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.seen_articles), f, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando artículos: {e}")
    
    def clean_text(self, text):
        """Limpiar texto para análisis"""
        return text.lower().replace('á', 'a').replace('é', 
'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    
    def search_news(self):
        """Buscar noticias relevantes"""
        print(f"🔍 Iniciando búsqueda - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        new_articles = []
        
        for source in self.sources:
            try:
                print(f"📰 Verificando: {source}")
                
                # Timeout para evitar cuelgues
                feed = feedparser.parse(source)
                
                if not feed.entries:
                    print(f"⚠️ Sin entradas en: {source}")
                    continue
                
                for entry in feed.entries[:10]:  # Solo primeros 10 para 
eficiencia
                    try:
                        # Contenido a analizar
                        title = getattr(entry, 'title', '')
                        summary = getattr(entry, 'summary', '')
                        content = f"{title} {summary}"
                        content_clean = self.clean_text(content)
                        
                        # Buscar keywords
                        found_keywords = []
                        for keyword in self.keywords:
                            keyword_clean = self.clean_text(keyword)
                            if keyword_clean in content_clean:
                                found_keywords.append(keyword)
                        
                        if found_keywords:
                            # ID único para evitar duplicados
                            article_id = 
hashlib.md5(f"{title}{entry.link}".encode('utf-8')).hexdigest()
                            
                            if article_id not in self.seen_articles:
                                article = {
                                    'title': title,
                                    'url': entry.link,
                                    'keywords': found_keywords,
                                    'date': getattr(entry, 'published', 
'Sin fecha'),
                                    'source': 
self.get_source_name(source),
                                    'id': article_id
                                }
                                
                                new_articles.append(article)
                                self.seen_articles.add(article_id)
                                print(f"✅ Nueva: {title[:50]}...")
                                
                    except Exception as e:
                        print(f"❌ Error procesando entrada: {e}")
                        continue
                        
            except Exception as e:
                print(f"❌ Error con fuente {source}: {e}")
                continue
        
        print(f"📊 Búsqueda completada: {len(new_articles)} noticias 
nuevas")
        return new_articles
    
    def get_source_name(self, url):
        """Extraer nombre legible de la fuente"""
        if 'elcomercio' in url:
            return '📰 El Comercio'
        elif 'eluniverso' in url:
            return '📰 El Universo'
        elif 'primicias' in url:
            return '📰 Primicias'
        elif 'google.com/news' in url:
            return '🔍 Google News'
        else:
            return '📰 Otra fuente'
    
    def get_emoji_for_keywords(self, keywords):
        """Emoji según tipo de noticia"""
        keywords_str = ' '.join(keywords).upper()
        
        if 'CONAIE' in keywords_str:
            return '🏛️'  # Político/institucional
        elif any(company in keywords_str for company in ['SOLGOLD', 
'DUNDEE', 'PLUSPETROL']):
            return '💰'  # Empresas
        elif 'MINERÍA' in keywords_str or 'MINERA' in keywords_str:
            return '⛏️'  # Minería general
        elif 'INDÍGENAS' in keywords_str or 'ANCESTRAL' in keywords_str:
            return '🌿'  # Pueblos indígenas
        else:
            return '📢'  # General
    
    def send_telegram_alert(self, article):
        """Enviar alerta por Telegram"""
        emoji = self.get_emoji_for_keywords(article['keywords'])
        
        # Truncar título si es muy largo
        title = article['title']
        if len(title) > 80:
            title = title[:77] + "..."
        
        message = f"""
{emoji} *NUEVA NOTICIA DETECTADA*

📰 *{title}*

🔗 [Leer completa]({article['url']})

🏷️ *Keywords:* {', '.join(article['keywords'][:3])}
📅 *Fecha:* {article['date']}
📋 *Fuente:* {article['source']}

#Ecuador #Noticias #{article['keywords'][0].replace(' ', '')}
        """
        
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            print(f"✅ Telegram enviado: {title[:30]}...")
            return True
            
        except Exception as e:
            print(f"❌ Error Telegram: {e}")
            # Intentar sin Markdown si falla
            try:
                simple_message = f"""
{emoji} NUEVA NOTICIA DETECTADA

{title}

Link: {article['url']}

Keywords: {', '.join(article['keywords'])}
Fuente: {article['source']}
                """
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=simple_message,
                    disable_web_page_preview=True
                )
                return True
            except:
                return False
    
    def run_search_cycle(self):
        """Ejecutar un ciclo completo de búsqueda"""
        try:
            print("\n" + "="*50)
            print("🚀 INICIANDO CICLO DE BÚSQUEDA")
            print("="*50)
            
            # Buscar noticias
            new_articles = self.search_news()
            
            if new_articles:
                print(f"📢 Enviando {len(new_articles)} alertas...")
                
                sent_count = 0
                for article in new_articles:
                    if self.send_telegram_alert(article):
                        sent_count += 1
                        time.sleep(2)  # Pausa entre mensajes
                
                # Guardar progreso
                self.save_seen_articles()
                
                print(f"✅ Enviadas {sent_count}/{len(new_articles)} 
alertas")
                
            else:
                print("📭 No hay noticias nuevas en este ciclo")
            
            print("="*50)
            print("✅ CICLO COMPLETADO")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ Error en ciclo de búsqueda: {e}")
            try:
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"⚠️ Error en monitor: {str(e)[:100]}"
                )
            except:
                pass

# Función principal
def main():
    """Función principal que mantiene el servicio activo"""
    print("🚀 Iniciando Ecuador News Monitor...")
    
    # Inicializar monitor
    monitor = EcuadorNewsMonitor()
    
    # Test inicial
    try:
        monitor.bot.send_message(
            chat_id=monitor.chat_id,
            text="🤖 Monitor de noticias Ecuador iniciado correctamente 
✅"
        )
        print("✅ Test de Telegram exitoso")
    except Exception as e:
        print(f"❌ Error en test de Telegram: {e}")
        return
    
    # Ejecutar búsqueda inicial
    monitor.run_search_cycle()
    
    # Programar búsquedas cada 2 horas
    schedule.every(2).hours.do(monitor.run_search_cycle)
    
    print("⏰ Programado: búsqueda cada 2 horas")
    print("🔄 Manteniendo servicio activo...")
    
    # Loop principal
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    except KeyboardInterrupt:
        print("\n👋 Deteniendo monitor...")

if __name__ == "__main__":
    main()
