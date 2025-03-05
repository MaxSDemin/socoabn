# -*- coding: utf-8 -*-

import sys
import os
import shutil
from PyQt5 import uic
from PyQt5 import QtCore, QtMultimedia
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog, \
    QTableWidgetItem
from PyQt5.QtWidgets import QGraphicsScene, QDialog, QSplashScreen
from PyQt5.QtGui import QPixmap, QBrush
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QTimer
import sqlite3


class Sokoban(QMainWindow):  # главный класс
    def __init__(self):
        super().__init__()
        uic.loadUi('forms/sokoban.ui', self)
        self.statusBar().showMessage('Готов')
        self.step_size = 40  # размер клетки главного окна
        self.zast()
        self.check_db()
        self.current_move = 0
        self.comleted_level = self.num_level_completed()
        self.level_selector = Level()
        self.level_selector.current_level = 1
        self.bind_button()
        self.create_scene()

    def check_db(self):  # проверка наличия рабочей БД
        if not os.path.isfile('database/sokoban_levels.db'):
            shutil.copyfile('database/start_database.db',
                            'database/sokoban_levels.db')  # создание копии
            #                                               первоналальной БД
        elif os.path.getsize('database/sokoban_levels.db') == 0:
            os.remove('database/sokoban_levels.db')
            shutil.copyfile('database/start_database.db',
                            'database/sokoban_levels.db')

    def bind_button(self):
        self.select_level.triggered.connect(self.sel_level)
        self.about1.triggered.connect(self.about)
        self.restart_level.triggered.connect(self.create_scene) # при выборе в меню рестарт
        self.import_txt.triggered.connect(self.start_conv)
        self.level_selector.closeWindow.connect(self.create_scene) # приём сигнала из объекта Level
        self.restart_level_2.clicked.connect(self.create_scene) # при нажатии на кнопку
        self.pushButton_back.clicked.connect(self.move_back)
        self.help_act.triggered.connect(self.help)

    def start_conv(self):
        self.conv = Converter()
        self.conv.show()

    def zast(self):  # подготовка и запуск заставки
        self.set_sounds()
        self.z = Zastavka()
        self.z.show()
        self.player_start.play()

    def set_sounds(self):  # создаёи 3 плеера
        media = QtCore.QUrl.fromLocalFile('sounds/shag4.mp3')
        # оъекс с сылкой на музыкальнвй файл для QMediaPlayer
        content = QtMultimedia.QMediaContent(media)
        # создание объекта преера
        self.player_step = QtMultimedia.QMediaPlayer()
        self.player_step.setMedia(content)  # звук шага

        media = QtCore.QUrl.fromLocalFile('sounds/win.mp3')
        content = QtMultimedia.QMediaContent(media)
        self.player_win = QtMultimedia.QMediaPlayer()
        self.player_win.setMedia(content)

        media = QtCore.QUrl.fromLocalFile('sounds/sokoban.mp3')
        content = QtMultimedia.QMediaContent(media)
        self.player_start = QtMultimedia.QMediaPlayer()
        self.player_start.setMedia(content)

    def create_scene(self):  # создание сцены
        self.history = []  # история ходов
        self.pushButton_back.setEnabled(False)
        self.level_selector.load_data_level()
        self.comleted_level = self.num_level_completed()

        self.sc = QGraphicsScene()  # новый объект. Чтобы размещать объекты на
        #                       сцены мы упаковываем координаты в объект QPointF
        #                       потому что этого требует объект сцены

        self.sc.setBackgroundBrush(QBrush(QPixmap('graphics/ground.png')))
        karta_row = self.level_selector.karta.split('\n')  # karta это только
                                                                # один уровень
        self.walls = []  # список для координат блоков стен
        self.crates = []   # сипсок для координат ящиков
        self.crates_obj = []    # список объектов ящиквов(для измениеня позиции
                                                          # ящиков в дальнейшем)
        self.places = []    # список координат мест дял ящика
        sokoman_coord = (0, 0)  # позиция игрока
        for y, row in enumerate(karta_row):
            for x, sym in enumerate(row):
                if sym == '@':
                    sokoman_coord = (x * self.step_size, y * self.step_size)
                    # ставим координаты человека чтобы поставить его сверху
                    #                                   всех объектов позже
                if sym == 'X':
                    # добовляем объект стен Pixmap на сцену по данным коорд.
                    self.sc.addPixmap(QPixmap('graphics/wall.png')).setPos(
                        x * self.step_size, y * self.step_size)
                    # добовляем координаты стен в список для сравнения позиции
                    # игрока и позиции стены
                    self.walls.append(
                        QPointF(x * self.step_size, y * self.step_size))
                if sym == '*':
                    # добовляем координаты ящиков в список
                    self.crates.append(
                        QPointF(x * self.step_size, y * self.step_size))
                if sym == '.':
                    # добовляем объект мест для ящиков Pixmap на сцену по
                    # данным координатам
                    self.sc.addPixmap(QPixmap('graphics/place.png')).setPos(
                        x * self.step_size, y * self.step_size)
                    # добовляем координаты местт для ящиков в список для сравнения позиции
                    # ящика и места для него
                    self.places.append(
                        QPointF(x * self.step_size, y * self.step_size))
        # отдельным циклом добвляем чтобы они были последними для дополнения
        for i in self.crates:
            self.crates_obj.append(self.sc.addPixmap(QPixmap('graphics/crate.png')))
            self.crates_obj[-1].setPos(i)
        self.sokoman = self.sc.addPixmap(QPixmap('graphics/soko.png'))
        self.sokoman.setPos(sokoman_coord[0], sokoman_coord[1])

        self.graphicsView.setScene(self.sc)  # отображение сцены в виджите

        self.current_move = 0
        self.start_pos = []
        self.start_pos.append(self.sokoman.pos())
        for _ in self.crates:  # добавляем в список координаиты человечка и ящиков
            self.start_pos.append(_)
        self.game_update()

    def add_move_to_history(self):
        if len(self.history) == 0:
            self.history.append(self.start_pos)  # добавление страртовой позиции
            #                                        в историю ходов
        current_hod = []
        current_hod.append(self.sokoman.pos())
        for i in self.crates:
            current_hod.append(i)
        self.history.append(current_hod)
        self.pushButton_back.setEnabled(True)
        self.flag = True

    def move_back(self):
        if self.flag:  # если отмена после хода
            self.history.pop()  # удаляем лишний последний элемент из истории
            self.flag = False
        back_hod = self.history.pop()  # записываем последний элемент
        self.sokoman.setPos(back_hod[0])    # задаём позицию предидущего положения сокомана
        self.current_move -= 1
        for i, coord in enumerate(back_hod[1:]):     # размещаем всё на сцене
            self.crates_obj[i].setPos(coord)
            self.crates[i] = coord
        if len(self.history) == 0:
            self.pushButton_back.setEnabled(False)
        self.game_update()

    def keyPressEvent(self, ev_key):
        if ev_key.key() == Qt.Key_Up:
            try_xy = QPointF(self.sokoman.pos().x(),
                             self.sokoman.pos().y() - self.step_size)
            if try_xy not in self.walls and try_xy not in self.crates:
                self.current_move += 1
                self.move_pos(self.sokoman, 'up')
            elif try_xy in self.crates:
                try_xy_crate = QPointF(try_xy.x(), try_xy.y() - self.step_size)
                if try_xy_crate not in self.walls and try_xy_crate not in self.crates:
                    idx = self.crates.index(try_xy)
                    self.move_pos(self.crates_obj[idx], 'up')
                    self.crates[idx] = self.crates_obj[idx].pos()
                    self.move_pos(self.sokoman, 'up')
                    self.current_move += 1

        if ev_key.key() == Qt.Key_Down:
            try_xy = QPointF(self.sokoman.pos().x(),
                             self.sokoman.pos().y() + self.step_size)
            if try_xy not in self.walls and try_xy not in self.crates:
                self.current_move += 1
                self.move_pos(self.sokoman, 'down')
            elif try_xy in self.crates:
                try_xy_crate = QPointF(try_xy.x(), try_xy.y() + self.step_size)
                if try_xy_crate not in self.walls and try_xy_crate not in self.crates:
                    idx = self.crates.index(try_xy)
                    self.move_pos(self.crates_obj[idx], 'down')
                    self.crates = []
                    for i in self.crates_obj:
                        self.crates.append(i.pos())
                    self.current_move += 1
                    self.move_pos(self.sokoman, 'down')

        if ev_key.key() == Qt.Key_Left:
            try_xy = QPointF(self.sokoman.pos().x() - self.step_size,
                             self.sokoman.pos().y())
            if try_xy not in self.walls and try_xy not in self.crates:
                self.current_move += 1
                self.move_pos(self.sokoman, 'left')
            elif try_xy in self.crates:
                try_xy_crate = QPointF(try_xy.x() - self.step_size, try_xy.y())
                if try_xy_crate not in self.walls and try_xy_crate not in self.crates:
                    idx = self.crates.index(try_xy)
                    self.move_pos(self.crates_obj[idx], 'left')
                    self.crates = []
                    for i in self.crates_obj:
                        self.crates.append(i.pos())
                    self.current_move += 1
                    self.move_pos(self.sokoman, 'left')

        if ev_key.key() == Qt.Key_Right:
            try_xy = QPointF(self.sokoman.pos().x() + self.step_size,
                             self.sokoman.pos().y())
            if try_xy not in self.walls and try_xy not in self.crates:
                self.current_move += 1
                self.move_pos(self.sokoman, 'right')
            elif try_xy in self.crates:
                try_xy_crate = QPointF(try_xy.x() + self.step_size, try_xy.y())
                if try_xy_crate not in self.walls and try_xy_crate not in self.crates:
                    idx = self.crates.index(try_xy)
                    self.move_pos(self.crates_obj[idx], 'right')
                    self.crates = []
                    for i in self.crates_obj:
                        self.crates.append(i.pos())
                    self.current_move += 1
                    self.move_pos(self.sokoman, 'right')

    def move_pos(self, obj, napr):
        self.player_step.play()
        if napr == 'down':
            obj.moveBy(0, self.step_size)
        elif napr == 'up':
            obj.moveBy(0, -1 * self.step_size)
        elif napr == 'right':
            obj.moveBy(self.step_size, 0)
        elif napr == 'left':
            obj.moveBy(-1 * self.step_size, 0)
        self.game_update()
        if obj == self.sokoman:
            self.add_move_to_history()
            if napr == 'down':
                obj.setPixmap(QPixmap('graphics/soko_face.png'))
            elif napr == 'up':
                obj.setPixmap(QPixmap('graphics/soko_back.png'))
            elif napr == 'right':
                obj.setPixmap(QPixmap('graphics/soko_right.png'))
            elif napr == 'left':
                obj.setPixmap(QPixmap('graphics/soko_left.png'))

    def game_update(self):  # обновление данных в окне
        self.label_level.setText(str(self.level_selector.current_level))
        self.label_move.setText(str(self.current_move))
        self.statusBar().showMessage(
            'Всего уровеней: ' + str(
                self.level_selector.totat_level) + '  Пройдено: ' + str(
                self.comleted_level))
        self.check_win()

    def num_level_completed(self): # при запуске проверяет количество пройденных
                                        # уровней и возвращает это число
        conn = sqlite3.connect("database/sokoban_levels.db")
        cursor = conn.cursor()
        num_completed = list(cursor.execute(
            '''select count(num_hod) from levels where complete = "yes"'''))[0][
            0]
        cursor.close()
        conn.close()
        return num_completed

    def check_win(self):  # сравнение координаты позиций ящиков с местами для ящиков
        for i in self.crates:
            if i not in self.places:
                return

        self.player_win.play()
        self.win = Win()
        self.win.show()

    def sel_level(self):
        self.level_selector.load_db()
        self.level_selector.show()

    def about(self):
        self.a = About()
        self.a.show()

    def help(self):
        self.help = Help()
        self.help.show()  #


class Win(QDialog):  # оповещение о победе в окне
    def __init__(self):
        super().__init__()
        uic.loadUi('forms/win_dialog.ui', self)
        self.pushButton.clicked.connect(self.close_win)
        self.label_3.setText(str(sokoban.current_move))
        query_num_hod = 'select num_hod, complete from levels where num_level = ' + str(
            sokoban.level_selector.current_level)
        query = 'update levels set complete = "yes", num_hod = ' + str(
            sokoban.current_move) + ' where num_level = ' + str(
            sokoban.level_selector.current_level)
        connect_bd = sqlite3.connect('database/sokoban_levels.db')
        cursor = connect_bd.cursor()
        num_hod = list(cursor.execute(query_num_hod))[0][0]
        yes_or_no = list(cursor.execute(query_num_hod))[0][1]
        if sokoban.current_move < num_hod or yes_or_no == 'no':
            cursor.execute(query)
            self.label.setPixmap(QPixmap('graphics/record.png'))
        else:
            self.label.setText('Уровень пройден!')
        connect_bd.commit()
        connect_bd.close()
        sokoban.level_selector.load_db()
        sokoban.level_selector.level_up()

    def close_win(self):
        sokoban.create_scene()
        self.close()


class Level(QDialog):  # считывание БД и отображение в QTableWidget
    closeWindow = pyqtSignal()  # создаём определитель сигнала

    def __init__(self):
        super().__init__()
        uic.loadUi('forms/select_level_dialog.ui', self)
        self.bind_button()
        self.header = ('Уровень', 'Ширина', 'Высота', 'Пройдено', 'Рекорд')
        #self.previons_row = 0
        self.load_db()

    def bind_button(self):
        self.pushButton.clicked.connect(self.select)  # продверждение
                                                        # выбора уровня
        self.checkBox.stateChanged.connect(self.filter_table)

    def load_db(self):
        connect_bd = sqlite3.connect('database/sokoban_levels.db')
        cursor = connect_bd.cursor()
        res = cursor.execute(
            '''select num_level, column, row, complete, num_hod 
            from levels''').fetchall()
        connect_bd.close()
        vyborka = []
        for i in res:
            vyborka.append(i)
        vyborka.sort(key=lambda x: x[0])  # сортировка по номеру уровня
        self.view_table(vyborka)
        self.totat_level = len(vyborka)  # сколько всего уровней в БД

    def level_up(self):  # прибавление уровней после успешного окончания
                            # предыдущего
        if self.current_level < self.totat_level:
            self.current_level += 1
        else:
            self.current_level = 1

    def select(self):  # button ОК
        row = self.table.currentRow()
        if row < 0:
            return
        self.current_level = int(self.table.item(row, 0).text())  # считывание
                                                # выбранного уровня в таблице
        self.closeWindow.emit()  # передаём сигнал(уровень выбран)
        self.hide()

    def load_data_level(self):  # получнение из БД ширины длины и рисунка карты
        connect_bd = sqlite3.connect('database/sokoban_levels.db')
        cursor = connect_bd.cursor()
        req = 'select column, row, level from levels where num_level = ' + str(
            self.current_level)
        res = cursor.execute(req).fetchone()
        data_level = list(res)
        self.karta_width = data_level[0]
        self.karta_height = data_level[1]
        self.karta = data_level[2]
        connect_bd.close()

    def view_table(self, sorted_list):  # отображаем таблицу
        num_col = len(sorted_list[0])   # количество колонок по первой строке
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.table.setColumnCount(num_col)
        for i, row in enumerate(sorted_list):   # заполняем таблицу по строчно
            self.table.setRowCount(self.table.rowCount() + 1)
            for k, item in enumerate(row):
                self.table.setItem(i, k, QTableWidgetItem(str(item)))
        self.table.setHorizontalHeaderLabels(self.header)  # делаем заглавки
        self.table.resizeColumnsToContents()    # растягиваем по содержимому

    def filter_table(self, state):  # обработка CheckBox(скрыть пройденные)
        # state передаётся из CheckBox(init)
        connect_bd = sqlite3.connect('database/sokoban_levels.db')
        cursor = connect_bd.cursor()
        if state == 0:
            # галка снята, вся БД считывается
            quwery = 'select num_level, column, row, complete, num_hod from levels'
        else:
            # галка есть, считываем только не пройденные
            quwery = 'select num_level, column, row, complete, num_hod from levels where complete = "no"'
        res = cursor.execute(quwery).fetchall()
        connect_bd.close()
        vyborka = []
        for i in res:
            vyborka.append(i)
        vyborka.sort(key=lambda x: x[0])  # сортировка по номеру уровня
        self.view_table(vyborka)


class About(QWidget):  # окно "о программе"
    def __init__(self):
        super().__init__()
        uic.loadUi('forms/about.ui', self)
        self.label.setText(
            '<pre style="text-align: center;"><strong>'
            '<span style="color:#A52A2A">О программе:</span></strong><br><br>'
            'Игра <span style="color:#0000FF">'
            '<strong>Sokoban </strong></span>создана <br>'
            'учеником 9&quot;К&quot; класса<br>'
            '<strong>Максимом Дёминым</strong></pre>'
            '2019 год')
        self.label_logo.setPixmap(QPixmap('graphics/logo.png'))


class Zastavka(QSplashScreen):  # отображение заставки без интерфейса окна с
                                                        # помощью QSplashScreen
    def __init__(self):
        super().__init__()
        # self.setWindowFlags(Qt.WindowStaysOnTopHint) # всегда остаётся поверх
        #                                                       других окон
        self.not_press()

    def press(self):
        self.setPixmap(QPixmap('graphics/zastavka2.jpg'))
        QTimer.singleShot(1000, self.not_press)

    def not_press(self):
        self.setPixmap(QPixmap('graphics/zastavka.jpg'))  # отображение заставки
        QTimer.singleShot(1000, self.press)  # создаём локальный таймер на 1с,
                                                # затем идём в метод press

    def mousePressEvent(self, em):
        self.close_zast()

    def keyPressEvent(self, ek):
        self.close_zast()

    def close_zast(self):  # закрываем заставку отображаем главное окно,
                                # тормозим заставочную музыку
        sokoban.show()
        sokoban.player_start.stop()
        self.close()


class Converter(QDialog):  # конвертация из текстового файла в базу данных
    def __init__(self):
        super().__init__()
        uic.loadUi('forms/converter.ui', self)
        self.bind_button()
        self.load_exist_db()
        self.new_levels = []

    def bind_button(self):
        self.open_file.clicked.connect(self.open_file_dialog)
        self.add_db.clicked.connect(self.add_in_db)
        self.pushButton_close.clicked.connect(self.close_self)
        self.pushButton_create_db.clicked.connect(self.new_db)

    def new_db(self):
        if os.path.isfile('database/sokoban_levels.db'):
            os.remove('database/sokoban_levels.db')
        shutil.copyfile('database/start_database.db',
                        'database/sokoban_levels.db')
        self.load_exist_db()
        sokoban.level_selector.current_level = 1
        sokoban.create_scene()
        self.pushButton_close.setEnabled(True)

    def load_exist_db(self):
        conn = sqlite3.connect("database/sokoban_levels.db")
        cursor = conn.cursor()
        len_db = list(cursor.execute('''select count(*) from levels'''))[0][0]
        cursor.close()
        conn.close()
        self.label_4.setText(str(len_db))

    def open_file_dialog(self):
        file_name = QFileDialog.getOpenFileName(self, 'Открыть файл', 'уровни',
                                                'Text Files(*.txt)')[0]
        with open(file_name, 'r') as data:
            text = data.read()
        list_row = text.split('\n')
        my_iter = iter(list_row)
        total_levels = 0
        i = 0
        k = len(list_row)
        while i < k - 1:
            level_txt = ''
            row = next(my_iter)
            i += 1
            if row == '*************************************':
                next(my_iter)
                i += 1
                next(my_iter)
                i += 1
                size_x = next(my_iter)[8:]
                i += 1
                size_y = next(my_iter)[8:]
                i += 1
                next(my_iter)
                i += 1
                next(my_iter)
                i += 1
                next(my_iter)
                i += 1
                for y in range(int(size_y)):
                    level_txt += next(my_iter) + '\n'
                    i += 1
                total_levels += 1
                self.new_levels.append((size_x, size_y, 'no', level_txt))
        self.label_2.setText(str(total_levels))
        if total_levels > 0:
            self.add_db.setEnabled(True)

    def add_in_db(self):
        conn = sqlite3.connect('database/sokoban_levels.db')
        cursor = conn.cursor()
        for zapis in self.new_levels:
            query = 'INSERT INTO levels(column, row, complete, num_hod, level) VALUES(' + \
                    zapis[0] + ',' + zapis[
                        1] + ', ' + \
                    '"' + zapis[2] + '", 0,"' + zapis[3] + '")'
            cursor.execute(query)
            print(query)
        conn.commit()
        cursor.close()
        conn.close()
        self.load_exist_db()
        self.add_db.setEnabled(False)
        self.pushButton_close.setEnabled(True)

    def close_self(self):
        sokoban.level_selector.load_db()
        sokoban.game_update()
        self.pushButton_close.setEnabled(False)
        self.close()


class Help(QWidget):  # помощь
    def __init__(self):
        super().__init__()
        with open('help.txt', 'r') as data:
            text = data.read()
        uic.loadUi('forms/help.ui', self)
        self.label_help.setText(text)
        self.label_help_2.setText('Чтобы выбрать уровень, в панеле задач нажмите'
                                  +'\n'+'Уровень-Выбрать...'
                                  +'\n'+'Чтобы добавить уровни, выберете Импорт-Импорт'
                                  +'\n'+'из текстового файла')#небольшое описание программы
        self.label_logo.setPixmap(QPixmap('graphics/help_windw.png'))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    sokoban = Sokoban()
    sokoban.move(350, 30)
    sys.exit(app.exec_())
