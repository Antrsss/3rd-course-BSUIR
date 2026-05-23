import pygame
import serial
import time
import random
import math

# Настройка Arduino
try:
    arduino = serial.Serial('COM5', 9600)
    time.sleep(2)
    arduino_connected = True
    print("Arduino подключена!")
except:
    arduino_connected = False
    print("Arduino не подключена, используем клавиатуру")

# Инициализация Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Arduino Space Shooter")
clock = pygame.time.Clock()

# Игровые переменные
player_x = 400
player_y = 500
player_width = 30
player_height = 20
bullets = []
enemies = []
medkits = []  # Аптечки
score = 0
health = 100
max_health = 100
inventory_medkits = 0
last_shot_time = 0
shot_delay = 300

# Таймеры
special_attack_ready = True
special_attack_cooldown = 10000
special_attack_last_used = 0

medkit_ready = True
medkit_cooldown = 30000
medkit_last_used = 0

# Новая система генерации аптечек
medkit_spawn_interval = 30.0  # 30 секунд между волнами
medkits_per_wave = random.randint(1, 2)  # 1-2 аптечки за волну
medkits_spawned_this_wave = 0
last_medkit_wave_time = time.time()
next_medkit_spawn_time = 0

# Цвета
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
DARK_GREEN = (0, 128, 0)
BRIGHT_GREEN = (0, 255, 0)

def read_arduino():
    if not arduino_connected:
        return None
        
    try:
        if arduino.in_waiting > 0:
            data = arduino.readline().decode().strip()
            if data:
                values = data.split(',')
                if len(values) == 5:  # Изменили с 6 на 5
                    return {
                        'joyX': int(values[0]),
                        'joyY': int(values[1]),
                        'btn1': bool(int(values[2])),  # Выстрел
                        'btn2': bool(int(values[3])),  # Аптечка
                        'joyBtn': bool(int(values[4])) # Спецатака (было values[5])
                    }
    except:
        pass
    return None

def send_to_arduino(command):
    if arduino_connected:
        try:
            arduino.write(command.encode())
        except:
            pass

def update_timers():
    global special_attack_ready, medkit_ready
    
    current_time = pygame.time.get_ticks()
    
    # Таймер спецатаки
    if not special_attack_ready:
        time_passed = current_time - special_attack_last_used
        if time_passed >= special_attack_cooldown:
            special_attack_ready = True
            send_to_arduino('SPECIAL_READY\n')
    
    # Таймер аптечки
    if not medkit_ready:
        time_passed = current_time - medkit_last_used
        if time_passed >= medkit_cooldown:
            medkit_ready = True
            send_to_arduino('MEDKIT_READY\n')
    
    return current_time


def draw_special_attack_indicator(screen):
    current_time = pygame.time.get_ticks()
    
    # Сдвигаем только прямоугольник вправо, текст остается на месте
    text_x = 450  # Фиксированная позиция для текста
    indicator_x = 600  # Прямоугольник сдвинут вправо от текста
    indicator_y = 20
    indicator_width = 80
    indicator_height = 20
    
    pygame.draw.rect(screen, GRAY, (indicator_x, indicator_y, indicator_width, indicator_height))
    
    if special_attack_ready:
        pygame.draw.rect(screen, GREEN, (indicator_x, indicator_y, indicator_width, indicator_height))
        status_text = "READY"
    else:
        time_passed = current_time - special_attack_last_used
        progress = min(time_passed / special_attack_cooldown, 1.0)
        fill_width = int(indicator_width * progress)
        pygame.draw.rect(screen, ORANGE, (indicator_x, indicator_y, fill_width, indicator_height))
        
        time_left = (special_attack_cooldown - time_passed) / 1000
        status_text = f"{time_left:.1f}s"
    
    font = pygame.font.Font(None, 24)
    text = font.render(f"SPECIAL: {status_text}", True, WHITE)
    screen.blit(text, (text_x, indicator_y))  # Текст всегда в одном месте
    pygame.draw.rect(screen, WHITE, (indicator_x, indicator_y, indicator_width, indicator_height), 2)

def draw_medkit_indicator(screen):
    current_time = pygame.time.get_ticks()
    
    # Сдвигаем только прямоугольник вправо, текст остается на месте
    text_x = 450  # Фиксированная позиция для текста
    indicator_x = 600  # Прямоугольник сдвинут вправо от текста
    indicator_y = 50
    indicator_width = 80
    indicator_height = 20
    
    pygame.draw.rect(screen, GRAY, (indicator_x, indicator_y, indicator_width, indicator_height))
    
    # Зеленый индикатор горит ТОЛЬКО когда есть аптечки в инвентаре И кд прошло
    if medkit_ready and inventory_medkits > 0:
        pygame.draw.rect(screen, BRIGHT_GREEN, (indicator_x, indicator_y, indicator_width, indicator_height))
        status_text = "READY"
    elif not medkit_ready:
        time_passed = current_time - medkit_last_used
        progress = min(time_passed / medkit_cooldown, 1.0)
        fill_width = int(indicator_width * progress)
        pygame.draw.rect(screen, DARK_GREEN, (indicator_x, indicator_y, fill_width, indicator_height))
        
        time_left = (medkit_cooldown - time_passed) / 1000
        status_text = f"{time_left:.1f}s"
    else:
        # Когда кд прошло, но нет аптечек в инвентаре
        status_text = "NO MED"
    
    font = pygame.font.Font(None, 24)
    text = font.render(f"MEDKIT: {status_text}", True, WHITE)
    screen.blit(text, (text_x, indicator_y))  # Текст всегда в одном месте
    pygame.draw.rect(screen, WHITE, (indicator_x, indicator_y, indicator_width, indicator_height), 2)
    
    count_text = font.render(f"x{inventory_medkits}", True, GREEN)
    screen.blit(count_text, (indicator_x + indicator_width + 10, indicator_y))

def use_special_attack():
    global special_attack_ready, special_attack_last_used
    
    if special_attack_ready:
        for i in range(5):
            angle = -30 + i * 15
            rad_angle = math.radians(angle)
            bullets.append({
                'x': player_x,
                'y': player_y - 10,
                'dx': math.sin(rad_angle) * 8,
                'dy': -math.cos(rad_angle) * 8
            })
        
        special_attack_ready = False
        special_attack_last_used = pygame.time.get_ticks()
        send_to_arduino('SPECIAL\n')
        return True
    return False

def use_medkit():
    global health, inventory_medkits, medkit_ready, medkit_last_used
    
    if medkit_ready and inventory_medkits > 0 and health < max_health:
        heal_amount = random.randint(5, 15)
        health = min(max_health, health + heal_amount)
        inventory_medkits -= 1
        
        medkit_ready = False
        medkit_last_used = pygame.time.get_ticks()
        send_to_arduino('MEDKIT\n')
        return True
    return False


def spawn_medkit():
    """Создает новую аптечку по новой системе - 1-2 раза за 30 секунд"""
    global last_medkit_wave_time, medkits_spawned_this_wave, medkits_per_wave, next_medkit_spawn_time
    
    current_time = time.time()
    
    # Проверяем, прошло ли 30 секунд с последней волны
    if current_time - last_medkit_wave_time >= medkit_spawn_interval:
        # Начинаем новую волну
        medkits_per_wave = random.randint(1, 2)  # 1-2 аптечки за волну
        medkits_spawned_this_wave = 0
        last_medkit_wave_time = current_time
        next_medkit_spawn_time = current_time + random.uniform(5, 25)  # Первая аптечка через 5-25 секунд
        print(f"Новая волна аптечек: {medkits_per_wave} штук")
    
    # Спавним аптечки по одной с задержкой
    if (medkits_spawned_this_wave < medkits_per_wave and 
        len(medkits) == 0 and  # Только если нет аптечек на экране
        current_time >= next_medkit_spawn_time):
        
        medkits.append({
            'x': random.randint(50, 750),
            'y': -30,
            'width': 20,
            'height': 20,
            'heal_amount': random.randint(5, 15),
            'speed': 2,
            'active': True
        })
        medkits_spawned_this_wave += 1
        
        # Устанавливаем время для следующей аптечки в этой волне (если есть)
        if medkits_spawned_this_wave < medkits_per_wave:
            next_medkit_spawn_time = current_time + random.uniform(5, 15)
        
        print(f"Аптечка создана! {medkits_spawned_this_wave}/{medkits_per_wave} в этой волне")

def show_victory_screen():
    """Показывает экран победы"""
    screen.fill((0, 0, 0))
    font_large = pygame.font.Font(None, 72)
    font_medium = pygame.font.Font(None, 36)
    
    victory_text = font_large.render("VICTORY!", True, GREEN)
    score_text = font_medium.render(f"Final Score: {score}", True, WHITE)
    congrats_text = font_medium.render("Congratulations! You reached 200 points!", True, YELLOW)
    
    screen.blit(victory_text, (400 - victory_text.get_width()//2, 200))
    screen.blit(score_text, (400 - score_text.get_width()//2, 300))
    screen.blit(congrats_text, (400 - congrats_text.get_width()//2, 350))
    
    pygame.display.flip()
    time.sleep(5)


def main_game():
    global player_x, player_y, bullets, enemies, medkits, score, health, inventory_medkits, last_shot_time
    
    running = True
    last_enemy_time = time.time()
    enemy_spawn_delay = 2.0
    
    while running:
        current_time = update_timers()
        pygame_time = pygame.time.get_ticks()
        
        # Проверка победы
        if score >= 200:
            show_victory_screen()
            running = False
            continue
        
        # Генерация аптечек по новой системе
        spawn_medkit()
        
        # Чтение данных с Arduino
        arduino_data = read_arduino()
        
        # Обработка событий Pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if pygame_time - last_shot_time > shot_delay:
                        bullets.append({
                            'x': player_x,
                            'y': player_y - 10,
                            'dx': 0,
                            'dy': -10
                        })
                        last_shot_time = pygame_time
                        send_to_arduino('FIRE\n')
                elif event.key == pygame.K_z:
                    use_special_attack()
                elif event.key == pygame.K_x:
                    use_medkit()
        
        # Управление от джойстика
        if arduino_data:
            if arduino_data['joyX'] < 300:
                player_x -= 8
            elif arduino_data['joyX'] > 700:
                player_x += 8
                
            if arduino_data['joyY'] < 300:
                player_y -= 5
            elif arduino_data['joyY'] > 700:
                player_y += 5
            
            if arduino_data['btn1'] and pygame_time - last_shot_time > shot_delay:
                bullets.append({
                    'x': player_x,
                    'y': player_y - 10,
                    'dx': 0,
                    'dy': -10
                })
                last_shot_time = pygame_time
                send_to_arduino('FIRE\n')
            
            if arduino_data['btn2']:
                use_medkit()
            
            if arduino_data['joyBtn']:
                use_special_attack()
        
        # Ограничение движения
        player_x = max(player_width//2, min(800 - player_width//2, player_x))
        player_y = max(player_height//2 + 400, min(600 - player_height//2, player_y))
        
        # Создание врагов
        if time.time() - last_enemy_time > enemy_spawn_delay:
            enemies.append({
                'x': random.randint(50, 750),
                'y': -30,
                'width': 30,
                'height': 20,
                'active': True,
                'speed': 4
            })
            last_enemy_time = time.time()
        
        # Движение пуль
        for bullet in bullets[:]:
            bullet['x'] += bullet['dx']
            bullet['y'] += bullet['dy']
            
            if (bullet['y'] < -10 or bullet['y'] > 610 or 
                bullet['x'] < -10 or bullet['x'] > 810):
                bullets.remove(bullet)
        
        # Движение врагов
        for enemy in enemies[:]:
            enemy['y'] += enemy['speed']
            
            player_rect = pygame.Rect(player_x-15, player_y-10, 30, 20)
            enemy_rect = pygame.Rect(enemy['x']-15, enemy['y']-10, 30, 20)
            
            if player_rect.colliderect(enemy_rect) and enemy['active']:
                enemies.remove(enemy)
                health -= 20
                send_to_arduino('CRASH\n')
                continue
            
            if enemy['y'] > 600:
                enemies.remove(enemy)
        
        # Движение и сбор аптечек
        for medkit in medkits[:]:
            medkit['y'] += medkit['speed']
            
            player_rect = pygame.Rect(player_x-15, player_y-10, 30, 20)

            medkit_rect = pygame.Rect(medkit['x']-10, medkit['y']-10, 20, 20)
            
            # Проверка столкновения с игроком
            if player_rect.colliderect(medkit_rect) and medkit['active']:
                medkit['active'] = False
                if health < max_health:
                    # Немедленное использование
                    health = min(max_health, health + medkit['heal_amount'])
                    send_to_arduino('HEAL\n')
                    print(f"Использована аптечка +{medkit['heal_amount']} HP")
                else:
                    # Сохранение в инвентарь
                    inventory_medkits += 1
                    send_to_arduino('MEDKIT_GET\n')
                    print(f"Аптечка добавлена в инвентарь! Всего: {inventory_medkits}")
                
                medkits.remove(medkit)
                continue
            
            # Удаление аптечек за экраном
            if medkit['y'] > 600:
                medkits.remove(medkit)
        
        # Столкновения пуль с врагами
        for bullet in bullets[:]:
            for enemy in enemies[:]:
                if (abs(bullet['x'] - enemy['x']) < 20 and 
                    abs(bullet['y'] - enemy['y']) < 20):
                    if bullet in bullets: 
                        bullets.remove(bullet)
                    if enemy in enemies: 
                        enemies.remove(enemy)
                    score += 10
                    send_to_arduino('HIT\n')
                    break
        
        # Отрисовка
        screen.fill((0, 0, 0))
        
        # Игрок
        pygame.draw.polygon(screen, GREEN, [
            (player_x, player_y - 15),
            (player_x - 15, player_y + 10),
            (player_x + 15, player_y + 10)
        ])
        
        # Пули
        for bullet in bullets:
            if bullet['dx'] == 0:
                pygame.draw.rect(screen, BLUE, (bullet['x']-2, bullet['y']-8, 4, 12))
            else:
                pygame.draw.circle(screen, YELLOW, (int(bullet['x']), int(bullet['y'])), 6)
        
        # Враги
        for enemy in enemies:
            pygame.draw.rect(screen, RED, (enemy['x']-15, enemy['y']-10, 30, 20))
            pygame.draw.circle(screen, YELLOW, (int(enemy['x']-8), int(enemy['y']+15)), 3)
            pygame.draw.circle(screen, YELLOW, (int(enemy['x']+8), int(enemy['y']+15)), 3)
        
        # Аптечки - рисуем красивые зеленые плюсики
        for medkit in medkits:
            # Зеленый квадрат как фон
            pygame.draw.rect(screen, DARK_GREEN, (medkit['x']-10, medkit['y']-10, 20, 20))
            
            # Белый плюсик
            pygame.draw.rect(screen, WHITE, (medkit['x']-5, medkit['y']-2, 10, 4))  # Горизонтальная линия
            pygame.draw.rect(screen, WHITE, (medkit['x']-2, medkit['y']-5, 4, 10))  # Вертикальная линия
            
            # Зеленая обводка
            pygame.draw.rect(screen, BRIGHT_GREEN, (medkit['x']-10, medkit['y']-10, 20, 20), 2)
            
            # Отладочная информация (можно убрать)
            font_small = pygame.font.Font(None, 16)
            heal_text = font_small.render(f"+{medkit['heal_amount']}", True, WHITE)
            screen.blit(heal_text, (medkit['x']-8, medkit['y']-25))
        
        # Интерфейс
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {score}", True, WHITE)
        health_text = font.render(f"Health: {health}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(health_text, (10, 50))
        
        # Индикаторы
        draw_special_attack_indicator(screen)
        draw_medkit_indicator(screen)
        
        # Подсказки - сдвинуты к центру
        if arduino_connected:
            controls_text = font.render("Move:Joystick | Shoot:BTN1 | Medkit:BTN2 | Special:JoyBtn", True, YELLOW)
        else:
            controls_text = font.render("Move:Arrows | Shoot:Space | Medkit:X | Special:Z", True, YELLOW)
        # Центрируем подсказку по горизонтали
        text_width = controls_text.get_width()

        screen.blit(controls_text, ((800 - text_width) // 2, 570))
        
        # Отладочная информация (можно убрать)
        debug_font = pygame.font.Font(None, 20)
        debug_text = debug_font.render(f"Medkits on screen: {len(medkits)} | In inventory: {inventory_medkits}", True, YELLOW)
        screen.blit(debug_text, (10, 90))
        
        # Проигрыш
        if health <= 0:
            game_over = font.render("GAME OVER - Score: " + str(score), True, RED)
            screen.blit(game_over, (250, 300))
            pygame.display.flip()
            time.sleep(3)
            running = False
        
        pygame.display.flip()
        clock.tick(60)
    
    if arduino_connected:
        arduino.close()
    pygame.quit()

if __name__ == "__main__":
    main_game()