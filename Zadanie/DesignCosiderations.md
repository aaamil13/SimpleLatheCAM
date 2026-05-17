freecad lathe tool camFreeCAD does not officially support CNC lathe (turning) operations out of the box. As of FreeCAD v1.0 and the upcoming v1.1 releases, the FreeCAD CAM Workbench is strictly optimized for 2.5D and 3-axis CNC milling.If you are looking to generate G-code for a lathe using FreeCAD, you must use unofficial workarounds or understand the fundamental limitations of the software.Current Status of Lathe CAM in FreeCADNo Built-in Turning Tools: Standard operations like profile, pocket, and face assume a vertical milling spindle and a rotating tool bit rather than a rotating workpiece.Broken Addons: Historical attempts to integrate turning, such as the TurningAddon based on the LibLathe Python library, are completely defunct and broken. The developers have noted that they no longer function due to major structural changes in the recent CAM Tool bit architecture.Milling Bias: The CAM workbench calculates clearances and toolpaths based on a standard endmill tool shape. It does not understand the unique profiles or geometric constraints of a triangular indexable lathe tool insert.The "Milling Workaround" for LathesWhile true lathe toolpaths are not supported, some users successfully trick FreeCAD into generating simple 2-axis lathe toolpaths by setting up a standard milling job with specific constraints:Map Your Axes: A standard CNC lathe uses the Z-axis for longitudinal movement (along the length of the part) and the X-axis for radial movement (the diameter).Model a 2D Profile: Draw the outer cross-section profile of your turned part using the FreeCAD Sketcher Workbench.Use the Profile Operation: Create a CAM Job and select the Profile tool. Instead of cutting a 3D solid, configure it to trace the 2D sketch lines.Tool Bit Substitution: Model your lathe tool as a standard endmill in the FreeCAD ToolBit Library Manager, making sure the diameter matches the nose radius of your turning insert.Remap G-code Output: Use the Axis Map dressup or modify a custom Python postprocessor script inside the Mod/CAM/Path/Post/scripts directory to swap the generated \(X/Y/Z\) coordinates into the \(X/Z\) format required by your lathe controller.Alternative Free Lathe CAM SoftwareBecause of the heavy adjustments required in FreeCAD, most hobbyists utilize external tools for turning operations:LinuxCNC Lathe Configurations: If your machine runs LinuxCNC, it includes built-in interactive wizard cycles for basic turning, face cuts, and threading, eliminating the need for a CAD/CAM program for simple parts.Fusion 360 (Personal Use): Offers a highly capable, fully-supported free tier turning CAM environment that accurately tracks tool inserts and collision clearances.If you would like to try the workaround, what CNC controller (e.g., LinuxCNC, GRBL, Mach3) does your lathe use? I can provide more details on customizing a postprocessor script for your specific machine.Отговорите на AI може да съдържат грешки. Научете повече13 сайтаNewbie question - Can FreeCad do lathe toolpaths?29.08.2023 г. — The Path Workbench can generate toolpaths that can be used on a simple CNC lathe (In fact, a Sherline lathe)FreeCAD ForumCAM FAQ - FreeCAD Documentation7.12.2025 г. — Other languages: * Deutsch. * English. * español. * français. * italiano. * polski. * русский ... At the moment, CAM Workbench can...FreeCAD Documentation(1) TURNING ADDON/LIBLATHE/CNC LATHE USE - FreeCAD Forum26.01.2026 г. — Re: TURNING ADDON/LIBLATHE/CNC LATHE USE ... Hello, There are no currently working extensions for lathes. LibLathe has been inacti...FreeCAD ForumПоказване на всичкипреди време бях намерил в github библиотека на pyhton която можеше да конфигурираш с какъв но работиш и да генерира на база зареденият модел g-code , потърси моля тъй като не мога да я намеря в моментаНай-вероятно библиотеката, за която се сещате, се казва LibLathe (или нейните копия като Schildkroet/LibLathe).Това е точно самостоятелна с отворен код Python библиотека, създадена специално за генериране на G-код за стругове (CNC Lathe). Тя работи по следния начин:Зарежда се моделът на детайла (профил).Конфигурира се инструментът (LLTool.py), с който ще се работи (параметри на стругарския нож).Библиотеката изчислява траекторията и генерира готовия G-код на базата на зададените операции (челно струговане, профилиране и т.н.).Защо е свързана с FreeCAD?Преди време тази библиотека беше основа на проекта FreeCAD Turning Addon, който се опитваше да я интегрира директно като разширение в CAM (Path) Workbench на FreeCAD.Други алтернативи, ако не е била тази:Ако проектът е бил малко по-различен, ето още две популярни Python библиотеки в GitHub за генериране на G-код по подобен начин:pygdk (Python G-code Development Kit) – Комплект за разработка, при който дефинирате таблица с инструменти (tools.json) и описвате операциите с Python код.Gscrib – По-нова и мощна Python библиотека за автоматизация на траектории, която поддържа управление на състоянието на машината и специфични контроли за инструменти.Ако си спомняте дали библиотеката имаше графичен интерфейс (GUI) или се управляваше изцяло през терминал/скрипт, споделете, за да ви насоча към точния софтуер.Отговорите на AI може да съдържат грешки. Научете повече5 сайтаSchildkroet/LibLathe: Python library for generating lathe paths ...GitHub - Schildkroet/LibLathe: Python library for generating lathe paths and gcode · GitHub.GitHubcnc4less/LibLathe: python library for generating lathe ... - GitHubLibLathe is an opensource standalone python library for generating lathe paths and gcode for use with cnc lathes.GitHubSupercharge G-code with Python. Gscrib helps CNC ... - GitHub19.11.2025 г. — Gscrib is a powerful Python library for generating G-code for CNC machines, 3D printers, and other automated devices. It provides ...GitHubПоказване на всичкинямаше гуи, само методи за работаТова, че библиотеката няма графичен интерфейс (GUI) и се управлява изцяло чрез код (методи и обекти), потвърждава на 100%, че сте работили точно с оригиналната LibLathe на cnc4less (или по-новата ѝ версия Schildkroet/LibLathe).Тя е проектирана точно като чист бекенд двигател (engine) за пресмятане на траектории. Ето как изглежда логиката на нейните методи в кода, за да се подсетите дали това е същият софтуер:Архитектурата на библиотеката (с която сте работили):Вместо GUI, вие импортирате специфични Python модули от библиотеката и извиквате методи за подаване на геометрията и конфигурация на ножа:Конфигуриране на режещия нож (LLTool.py): Дефинира се формата на пластината (insert), нейния радиус на заобляне на върха (nose radius), ъгли на рязане и посока на инструмента (ляв/десен нож).Зареждане на детайла (LLSegment.py / LLPoint.py): Профилът на детайла се описва чисто математически като поредица от точки, линии и дъги чрез подаване на координати към методи за вектори и сегменти.Избор на операция: Извикват се методите за конкретни цикли – например LLFaceOP.py (за челно струговане) или LLProfileOP.py (за финишно/грубо надлъжно профилиране).Генериране на G-код: Накрая се извиква функция, която пресмята отнемането на материала слой по слой (от отместването на сегментите) и записва текстовия .nc или .gcode файл.Къде да я намерите в GitHub:Официалният сорс код: Можете да изтеглите проекта от GitHub хранилището на Schildkroet/LibLathe.Примери за употреба: В папката /examples вътре в хранилището има готови скриптове (като например defeature_example.py), които показват как точно се извикват методите в чист Python скрипт без графична обвивка.Инсталация: Тъй като е чиста библиотека, тя може да се инсталира в Python средата ви директно през терминала с командата: pip install liblathe.Ако имате нужда от помощ за това как да стартирате някой от базовите примери в терминала или искате да разгледаме структурата на методите за конфигуриране на инструмента, кажете ми коя част искате да тестваме!Отговорите на AI може да съдържат грешки. Научете повече4 сайтаSchildkroet/LibLathe: Python library for generating lathe paths ...Table_title: Schildkroet/LibLathe Table_content: header: | Name | Name | Last commit message | Last commit date | row: | Name: Lat...GitHubcnc4less/LibLathe: python library for generating lathe ... - GitHubTable_title: cnc4less/LibLathe Table_content: header: | Name | Name | Last commit message | Last commit date | row: | Name: Latest...GitHubdubstar-04/LibLathe: Python library for generating lathe paths ...LibLathe is an opensource standalone python library for generating turning paths and gcode for use with cnc lathes. | ⚠️ WARNING: ...GitHubПоказване на всичкиобмислям добавка за струг linuxcnc, с която да можеш лесно да конфигурираш детайл, нож и материал, така че да спестя дългият път на изграждане на датайл в кад, конверт към g-code и прехвърляне към цнц; обмислям да използвам CadQuery или подобена кад библиотека за изграждане на готови форми с параметри ( цилиндър, под ъгъл, chamfer, fillet, и дръги като готови плъгин които да могат да се добавят към базовият едитор ) , да задавам и ножа който да се визуализира коректно; какаво мислиш и как би реализирал такова разширение към linuxcncТова е изключително силна и практична идея. В индустрията този подход се нарича Диалогово програмиране (Conversational Programming) или Shop-Floor Programming (както е при Mazak Mazatrol или Haas Intuitive Programming). Струговите операции са перфектни за това, тъй като в 95% от случаите детайлите са просто 2D профили, въртящи се около една ос (Z), и преминаването през тромавата верига CAD \(\rightarrow \) CAM \(\rightarrow \) Postprocess \(\rightarrow \) CNC за един прост фланец или болт е чиста загуба на време.Изборът на CadQuery е отличен, защото тя е базирана на мощното геометрично ядро OpenCASCADE, което позволява лесно вадене на 2D сечения (профили) от 3D обекти чрез методи като .section() или .project().Архитектура на разширението (Как бих го реализирал)За да се интегрира софтуерът безпроблемно с LinuxCNC, най-чистият начин е разработването на потребителски интерфейс (GUI Layout), който работи като самостоятелен таб или екран в модерните LinuxCNC интерфейси като QtPyVCP или Axis.Проектът трябва да бъде разделен на 4 независими модула:[ Parametric Engine (CadQuery) ] 
               │
               ▼
   [ 2D Profile Extractor ] ──> [ Visualizer (PyQt / PyOpenGL) ]
               │
               ▼
   [ CAM Engine (LibLathe / Custom) ] ──> [ Tool & Material Library ]
               │
               ▼
   [ G-code Generator & LinuxCNC Injector ]
1. Параметричен конфигуратор (CadQuery + С택 от операции)Вместо потребителят да пише код, вие дефинирате списък от готови геометрични примитиви (плъгини). Потребителят ги подрежда в интерфейса като дърво или последователност:Базов заготовка (Stock): Диаметър и дължина (напр. cq.Workplane().cylinder(L, D/2)).Конструктивни елементи (Features): Стъпало (Cylinder), Конус/Наклон (Taper), Закръгление (Fillet), Фаска (Chamfer), Нарез (Thread groove).CadQuery обединява тези елементи чрез булеви операции (събиране/изваждане), след което извлича горния 2D контур на детайла по оста X-Z.2. Модул за инструменти и материали (Библиотека)Нож: Дефинира се геометрично: радиус на върха (\(R_{\epsilon }\)), водещ ъгъл (\(\kappa _{r}\)), ориентация (ляв/десен/челен) и тип (за грубо, за фино, за резба).Материал: База данни (Алуминий, Стомана 45, Месинг), която автоматично изчислява препоръчителна скорост на рязане (\(V_{c}\) в м/мин) и подаване (\(f\) в мм/оборот).3. CAM Ядро (Генериране на траекторията)Тъй като CadQuery само дава крайната геометрия, ви трябва алгоритъм, който да разбере как да премине от суровата цилиндрична заготовка до финалния профил.Тук можете да използвате LibLathe като чист бекенд, на който подавате 2D точките от CadQuery и параметрите на ножа.Алгоритъмът изчислява слоевете за грубо струговане (Roughing) на база максималната дълбочина на рязане (\(a_{p}\)), която ножът и материалът позволяват, последвани от един финишен проход (Finishing), отчитайки радиуса на ножа (\(R_{\epsilon }\)).4. Визуализация и интерфейс (LinuxCNC QtPyVCP)Най-добре е интерфейсът да се изгради с QtPyVCP (базиран на PyQt5). Той е официално поддържан от LinuxCNC общността и се интегрира перфектно.За визуализация на детайла и ножа в реално време (преди рязане) се използва PyQtGraph или PyOpenGL прозорец, който чертае 2D профила на детайла, получената траектория на инструмента и контура на самия нож, за да се види дали няма да има сблъсък на държача (holder) с детайла.Пътна карта за разработка (Стъпка по стъпка)Фаза 1: CAM Скрипт (Доказване на концепцията)Напишете чист Python скрипт (без GUI). Използвайте CadQuery, за да генерирате детайл със стъпало и фаска. Извадете координатите на профила и ги подайте на LibLathe. Генерирайте G-код и го тествайте в симулатора на LinuxCNC.Фаза 2: Изграждане на графичния интерфейс (QtPyVCP)Създайте екран с таблица/списък, където потребителят може да натисне бутон + Добави операция, да избере "Фаска" и да въведе нейния размер. При всяка промяна CadQuery трябва да преизчислява 3D модела на заден фон и да обновява 2D чертежа на екрана.Фаза 3: Динамично инжектиране в LinuxCNCИзползвайте Python библиотеката linuxcnc (вградена в машината), за да заредите генерирания G-код директно в работещия интерфейс чрез метода linuxcnc.command().program_open(filename).Защо този проект ще бъде успешен?Общността на LinuxCNC отчаяно се нуждае от модерен, отворен софтуер за диалогово струговане. Повечето съществуващи решения (като вградените макроси на Axis) изглеждат остарели и не поддържат комплексна визуализация и библиотеки за инструменти. Използването на Python + CadQuery + QtPyVCP ще направи кода ви модулен, лесен за поддръжка и изключително разширяем с нови плъгини за специфични детайли.Ако искате да започнем с прототипа, можем да напишем първия базов Python скрипт, който дефинира CadQuery модел, извлича координатите му и изчислява прост G-код. Имате ли вече инсталирана CadQuery среда на компютъра ви?Отговорите на AI може да съдържат грешки. Научете повечемислех за GMOCCAPY или QtDragon GUIИзборът между GMOCCAPY и QtDragon променя изцяло стратегията на разработка, като и двата интерфейса предлагат фантастични, но коренно различни предимства за вашия проект.Тъй като и двата поддържат вградени табове (Embedded Tabs), вие няма нужда да пренаписвате целия интерфейс. Вашето разширение ще бъде просто един нов таб в тях, наречен например „Диалогов CAM“.Ето как се съпоставят двата избора спрямо вашата цел (CadQuery + Струг):Вариант 1: QtDragon (Силно препоръчителният избор за CadQuery)QtDragon и QtDragon_hd са изградени върху модерната рамка QtVCP (базирана на PyQt5). Това ги прави технологично перфектния партньор за CadQuery.Предимство (Технологично съответствие): Понеже QtDragon е чист PyQt5, вашият CAM таб може да бъде написан директно като PyQt5 прозорец. Интеграцията на 2D графики или 3D визуализация през PyQtGraph / PyOpenGL става естествено, без конфликти между графичните библиотеки.Гъвкавост в интерфейса: Можете да добавите вашия CAM плъгин в tabWidget_utilities (помощните табове долу/встрани) или в stackedWidget_mainTab (където с натискане на бутон „User“ вашият CAM заема целия главен екран).Минус: Дизайнът на QtDragon е силно ориентиран към мишка/клавиатура (въпреки че има вградена виртуална клавиатура за тъчскрийн).Как се вгражда в INI файла на LinuxCNC:ini[DISPLAY]
DISPLAY = qtdragon
EMBED_TAB_NAME = Диалогов CAM
EMBED_TAB_LOCATION = stackedWidget_mainTab
EMBED_TAB_COMMAND = python3 /path/to/your/cadquery_cam_tab.py -x {XID}
Използвайте кода внимателно.(Параметърът -x {XID} предава идентификатора на прозореца на LinuxCNC, за да може вашият Python скрипт да се "залепи" в таба).Вариант 2: GMOCCAPY (Кралят на тъчскрийн управлението)GMOCCAPY е легендарен интерфейс, проектиран специално за индустриални тъчскрийн монитори с големи бутони.Предимство (Стругов режим): GMOCCAPY има страхотен вграден стругов режим (Lathe mode), който поддържа графично визуализиране както за нормален нож (пред детайла), така и за заден нож (Back tool lathe). Той автоматично превключва DRO дисплеите между радиус и диаметър според G-кода (G7/G8). Ако машината ви ще се управлява с мазен тъчскрийн директно в цеха, GMOCCAPY осигурява най-добрата ергономия.Минус (Графична сложност): GMOCCAPY е базиран на по-старата библиотека GTK / GladeVCP. Тъй като CadQuery и модерните Python 3 визуализатори работят много по-лесно с Qt (PyQt5), ще трябва да вграждате Qt приложение вътре в GTK интерфейс чрез qtvcp_embed. Това е напълно възможно и поддържано от LinuxCNC, но добавя един слой сложност при прехвърлянето на данни.Как се вгражда в INI файла на LinuxCNC:ini[DISPLAY]
DISPLAY = gmoccapy
EMBED_TAB_NAME = Диалогов CAM
EMBED_TAB_LOCATION = ntb_preview
EMBED_TAB_COMMAND = halcmd loadusr -Wn qtvcp_embed qtvcp -d -c qtvcp_embed -x {XID} /path/to/your/cadquery_cam_tab.py
Използвайте кода внимателно.(Тук използваме qtvcp_embed като мост, за да заредим вашето Qt/CadQuery приложение вътре в GTK таба на GMOCCAPY).Моята препоръка за архитектура на кодаТъй като целта ви е да избягате от тромавия CAD/CAM процес, най-бързият път до работещ прототип е QtDragon. С него ще си спестите главоболията по напасване на графичните библиотеки.Вашият Python скрипт (cadquery_cam_tab.py) трябва да наследява QWidget от PyQt5 и да изглежда по следния начин в основата си:pythonimport sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget
import linuxcnc  # Вграденият модул на LinuxCNC за управление на машината

class DialogCamTab(QWidget):
    def __init__(self, window_id=None):
        super().__init__()
        self.layout = QVBoxLayout(self)
        
        # 1. Интерфейс за параметри (Пример: таблица с операции)
        self.table = QTableWidget(5, 3)
        self.table.setHorizontalHeaderLabels(["Операция", "Диаметър (X)", "Дължина (Z)"])
        self.layout.addWidget(self.table)
        
        # 2. Бутон за генериране и пускане
        self.btn_run = QPushButton("Генерирай и зареди в LinuxCNC")
        self.btn_run.clicked.connect(self.generate_and_inject)
        self.layout.addWidget(self.btn_run)
        
        # Връзка към командния център на LinuxCNC
        self.command = linuxcnc.command()

    def generate_and_inject(self):
        # ТУК: Извикване на CadQuery -> Вадене на 2D профил -> Изчисляване на G-код с LibLathe
        gcode_path = "/home/cnc/nc_files/dialog_output.ngc"
        
        # Записваме G-кода във файл
        with open(gcode_path, "w") as f:
            f.write("G21 G18 G90 G40\n") # Милиметри, Стругова равнина XZ...
            f.write("(Тук ще е генерираният код от LibLathe)\n")
            f.write("M30\n")
            
        # Автоматично инжектиране и зареждане в главния екран на LinuxCNC
        self.command.program_open(gcode_path)

if __name__ == "__main__":
    # Логика за интеграция чрез XID (за вграждане в таб)
    app = QApplication(sys.argv)
    # Код за прихващане на -x {XID} аргумента от LinuxCNC...
    ex = DialogCamTab()
    ex.show()
    sys.exit(app.exec_())
Използвайте кода внимателно.Кой от двата интерфейса визуално ви допада повече за физическата ви машина? Ако машината ви е с тъчскрийн, можем да разгледаме как точно да направим моста към GMOCCAPY, или ако предпочитате по-чист код – да се фокусираме върху пълната реализация за QtDragon.Отговорите на AI може да съдържат грешки. Научете повече9 сайтаQtDragon GUI - LinuxCNC15.12.2025 г. — You can optionally embed QtVCP Virtual Control Panels into the QtDragon or QtDragon_hd screen. These panels can be either user bui...LinuxCNCGMOCCAPY - LinuxCNC18.07.2023 г. — The second line is optional and will switch the X axis in a way you need for a back tool lathe. Also the keyboard shortcuts will r...LinuxCNCQtDragon GUI - LinuxCNC8.05.2026 г. — 2. Начало работы — INI-файл If your configuration is not currently set up to use QtDragon, you can change it by editing the INI fi...LinuxCNCПоказване на всичкиGTK мисля че са докладвани много фииз фраме и бавна реакция с по голямо натоварване на процесора ( проблем на GTK  ); от друга страна QtDragon е по нов и по малко дефиниран ( възможни са промени в стандарта ) , но пък работи по стабилно с python допълнения; изглежда избора ще е QtDragon но трабва да се дефинират отделно точките на взаймодействие с linuxcnc, така че да имаме ниво на изолзция, ако в бъдеще се появят разлики в интерфейсите; виждам и ограничения на резолюцията - QtDragon_lathe is a modified version of QtDragon more suitable for lathes.
It is resizable from a resolution of 1280x768 to 1680x1200.Напълно сте прав за техническия анализ. GTK2 (основата на GMOCCAPY) има сериозни архитектурни проблеми с опресняването на графичния буфер под Linux, което води до висока консумация на процесорно време (CPU spikes), когато се чертае динамична графика или се въртят сложни траектории.Изборът на QtDragon (и по-конкретно специализираната версия QtDragon_lathe) е правилното инженерно решение за 2026 г. Той е изграден върху PyQt5, където обработката на сигнали и интерфейсните нишки работят много по-чисто с Python обекти. Ограничението в резолюцията (от 1280x768 нагоре) също е стандарт за модерните индустриални тъчскрийн монитори.За да се предпазите от бъдещи промени в LinuxCNC (разлики между версии 2.9, 3.0 и нагоре) или евентуална смяна на интерфейса в бъдеще, трябва да приложите софтуерния патърн "Слой на изолация" (Abstraction Layer).Ето как да проектирате архитектурата на вашето разширение, така че ядрото (CadQuery + CAM) да бъде напълно независимо от графичната обвивка:Архитектура с ниво на изолация (Clean Architecture)Разделяме проекта на три напълно независими слоя. Всеки слой комуникира със съседния само през строго дефиниран интерфейс (API).┌─────────────────────────────────────────────────────────┐
│              СЛОЙ 1: ГРАФИЧЕН ИНТЕРФЕЙС (UI)           │
│  - QtDragon_lathe Embedded Tab (PyQt5)                  │
│  - Списък с операции, Бутони, Полета за диаметри        │
└────────────────────────────┬────────────────────────────┘
                             │ Изпраща речник (Dict) с данни
                             ▼
┌─────────────────────────────────────────────────────────┐
│          СЛОЙ 2: ОСТРОВ НА ИЗОЛАЦИЯ (CAM БЕКЕНД)        │
│  - CadQuery: Генерира 3D и вади 2D профила             │
│  - LibLathe: Изчислява проходите и отнемането на метал  │
│  - Извежда чист G-код като СТРИНГ (String)              │
└────────────────────────────┬────────────────────────────┘
                             │ Подава чист G-код текст
                             ▼
┌─────────────────────────────────────────────────────────┐
│        СЛОЙ 3: ДРАЙВЕР ЗА СВЪРЗВАНЕ С LINUXCNC          │
│  - Капсулира вградената библиотека 'import linuxcnc'    │
│  - Ако LinuxCNC се промени, променяме САМО този файл   │
└─────────────────────────────────────────────────────────┘
Практическа реализация (Примерен код за архитектурата)1. Слой 3: linuxcnc_driver.py (Изолираната връзка с машината)Този скрипт се грижи единствено за комуникацията с LinuxCNC. Ако утре преминете към друг интерфейс или LinuxCNC смени софтуерната си библиотека, вие ще редактирате само този файл.python# linuxcnc_driver.py
import os

try:
    import linuxcnc
    HAS_LINUXCNC = True
except ImportError:
    HAS_LINUXCNC = False  # Позволява ни да тестваме софтуера на Windows/Mac без машина!

class LinuxCNCDriver:
    def __init__(self):
        if HAS_LINUXCNC:
            self.command = linuxcnc.command()
            self.stat = linuxcnc.stat()
        else:
            self.command = None
            self.stat = None

    def inject_gcode(self, gcode_text: str, filename="dialog_cam_output.ngc"):
        """Записва G-кода и го зарежда директно в LinuxCNC"""
        # Намиране на директорията за NC файлове (може да се вземе и от INI)
        nc_dir = os.path.expanduser("~/linuxcnc/nc_files")
        if not os.path.exists(nc_dir):
            os.makedirs(nc_dir)
            
        filepath = os.path.join(nc_dir, filename)
        
        # Запис на диска
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(gcode_text)
            
        # Инжектиране в активния интерфейс (QtDragon)
        if HAS_LINUXCNC and self.command:
            self.command.program_open(filepath)
            return True
        else:
            print(f"[СИМУЛАЦИЯ] G-кодът е записан успешно в: {filepath}")
            return False

    def get_machine_status(self):
        """Връща състоянието на машината в неутрален формат"""
        if HAS_LINUXCNC and self.stat:
            self.stat.poll()
            return {
                "estop": self.stat.estop,
                "current_tool": self.stat.tool_in_spindle,
                "file_loaded": self.stat.file
            }
        return {"estop": 0, "current_tool": 1, "file_loaded": "Simulation"}
Използвайте кода внимателно.2. Слой 2: cam_engine.py (Ядрото - CadQuery + LibLathe)Този слой не знае нищо за QtDragon и не знае нищо за LinuxCNC. Той просто получава размери, смята геометрия и връща текст с G-код.python# cam_engine.py
# Тук в бъдеще ще импортирате cadquery и liblathe

class DialogCAMEngine:
    def __init__(self):
        pass

    def generate_lathe_code(self, operations: list, tool_data: dict, material_data: dict) -> str:
        """
        operations: списък от речници, напр: [{'type': 'cylinder', 'D': 40, 'L': 50}, {'type': 'chamfer', 'size': 2}]
        """
        # СТЪПКА 1: Изграждане на 3D модела в CadQuery на база 'operations'
        # СТЪПКА 2: Извличане на 2D сечението (профила) чрез CadQuery .section()
        # СТЪПКА 3: Подаване на точките към LibLathe, съобразявайки tool_data (ножа)
        
        # Примерно генериран тестов G-код за струг (G18 - XZ равнина)
        gcode = []
        gcode.append("G21 G18 G90 G40 G95") # Метрична система, Стругова равнина, Абсолютни коорд, Подаване на оборот
        gcode.append(f"T{tool_data['id']} M6") # Смяна на нож
        gcode.append(f"S{material_data['speed']} M3") # Обороти и посока на шпиндела
        
        # Симулиране на траектория по Х и Z (Диаметрално програмиране)
        gcode.append("G00 X50.0 Z5.0")
        gcode.append("G01 Z-30.0 F0.2")
        gcode.append("G01 X55.0")
        gcode.append("G00 Z5.0")
        
        gcode.append("M5 M9") # Спиране на шпиндел и охлаждане
        gcode.append("M30")   # Край на програмата
        
        return "\n".join(gcode)
Използвайте кода внимателно.3. Слой 1: ui_tab.py (Интерфейсът за QtDragon)Това е скриптът, който LinuxCNC извиква чрез EMBED_TAB_COMMAND в INI файла. Той само събира данните от потребителя през екрана и ги препраща надолу по веригата.python# ui_tab.py
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QApplication
from cam_engine import DialogCAMEngine
from linuxcnc_driver import LinuxCNCDriver

class QtDragonEmbedTab(QWidget):
    def __init__(self):
        super().__init__()
        self.engine = DialogCAMEngine()
        self.cnc = LinuxCNCDriver()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel("Параметричен стругов CAM", self)
        self.layout.addWidget(self.label)
        
        # Бутон за действие
        self.btn_generate = QPushButton("Изчисли и Зареди", self)
        self.btn_generate.clicked.connect(self.handle_generation)
        self.layout.addWidget(self.btn_generate)

    def handle_generation(self):
        # 1. Събиране на данни от UI форматите (в момента симулирани)
        mock_ops = [{'type': 'cylinder', 'D': 40, 'L': 50}]
        mock_tool = {'id': 1, 'radius': 0.4}
        mock_material = {'speed': 1200}
        
        # 2. Извикване на изолираното CAM ядро
        gcode = self.engine.generate_lathe_code(mock_ops, mock_tool, mock_material)
        
        # 3. Извикване на изолирания драйвер за инжектиране
        self.cnc.inject_gcode(gcode)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tab = QtDragonEmbedTab()
    tab.show()
    sys.exit(app.exec_())
Използвайте кода внимателно.Какво печелите от тази изолация?Разработка без LinuxCNC: Можете да пишете и тествате CadQuery логиката и интерфейса на личния си лаптоп (Windows/Mac). Драйверът автоматично ще разпознае, че липсва LinuxCNC, и просто ще записва тестови файлове, вместо да дава грешка.Бъдеща съвместимост: Ако утре LinuxCNC преминат към изцяло нов уеб-базиран интерфейс или променят Python API-то си, cam_engine.py остава недокоснат.Искате ли да се фокусираме върху геометричната част в cam_engine.py? Можем да напишем примерен CadQuery код, който изгражда детайл с фаска и извлича 2D масив от точки на контура (X, Z), готов за обработка.Отговорите на AI може да съдържат грешки. Научете повечепърво да помислим кой патх генератора да ползваме либлате не се поддържа от доста време, докато pygdk капсулира г-код в методи , което изглежда интерресно като идея; помисли и за други варианти които да са приложими ; в pygdk не виждам и подръжка на инструментаПравилно сте забелязали фундаменталните проблеми на съществуващите решения. Schildkroet/LibLathe е изоставен преди години и няма да работи с модерен Python 3, без да пренапишете половината му ядро.От друга страна, cilynx/pygdk предлага много елегантен и модерен обектно-ориентиран подход (капсулиране на G-код в методи), но липсата на поддръжка за радиус и геометрия на инструмента (ножа) го прави неизползваем за струговане. При струга радиусът на режещата пластина (например \(R=0.4\) или \(0.8\) мм) променя драстично траекторията при конуси (tapers) и закръгления (fillets) – ако кодът не прави компенсация на радиуса (Tool Nose Radius Compensation), детайлът ще излезе извън допуските.Ако искаме стабилно, поддържано и професионално решение за траекториите, трябва да разгледаме други алтернативи или да комбинираме най-доброто от тях. Ето 3 реално приложими варианта:Вариант 1: Вградените Canned Cycles (Цикли) на LinuxCNC (Най-чистият инженерен подход)Вместо да пресмятате стотици редове от фини G1/G2/G3 движения в Python, можете да използвате вградения интелект на самия LinuxCNC контролер. LinuxCNC поддържа мощни стругови цикли:G71 / G72: Цикли за грубо надлъжно и челно струговане (Roughing Cycles).G70: Цикъл за финишно оформяне (Finishing Cycle).G41 / G42: Автоматична хардуерна компенсация на радиуса на ножа (G42 за заден нож, G41 за преден).Как работи в нашия случай:Вашият CadQuery скрипт извлича чистите 2D точки на финалния профил.Вашият Python скрипт генерира много кратък G-код файл, който просто описва контура между O100 sub и O100 endsub (подпрограма).Преди подпрограмата извиквате G71 P100 Q101 D2.0 I0.5 R1.0 (където D2.0 е дълбочината на рязане на слой, а I0.5 е оставен материал за финиш).Резултат: LinuxCNC сам пресмята проходите за грубо отнемане в реално време, съобразявайки ножа дефиниран в неговата собствена таблица с инструменти (tool.tbl).Предимства: Нулев риск от бъгове в CAM алгоритъма; перфектно напасване с машината; минимален Python код.Недостатъци: Трябва да се съобразят спецификите на G71/G72 в LinuxCNC (изискват монотонно нарастване/намаляване на профила).Вариант 2: OpenCAMLib (ocl) – Индустриалният стандарт с отворен кодOpenCAMLib (ocl) е изключително мощна C++ библиотека с официални Python бруйдъри (bindings), която се използва активно от FreeCAD за изчисляване на сложни 3D траектории.Как се прилага за струг: Библиотеката поддържа т.нар. Drop-Cutter и Push-Cutter алгоритми. Тя ви позволява да дефинирате точната геометрия на инструмента (поддържа цилиндрични, сферични и конични фрези, които лесно се конфигурират математически като стругарски пластини). Подавате 3D STL или сечение от CadQuery и библиотека изчислява точните координати за отнемане на материал, компенсирайки формата на ножа.Предимства: Изключително бърза (написана на C++), активно поддържана, индустриално тествана.Недостатъци: Малко по-сложна за инсталация (изисква компилация или специфичен pip install opencamlib).Вариант 3: Написване на собствено "Микро CAM Ядро" в PythonТъй като струговането е 2D операция в една равнина (X-Z), математиката зад грубото отнемане на материала не е толкова сложна. Можете да създадете ваш собствен модул за траектории, стъпвайки върху концепцията на pygdk (капсулиране в методи), но добавяйки поддръжка на инструмент.Можете да използвате геометричната Python библиотека Shapely за пресмятане на проходите:Дефинирате заготовката като 2D полигон (правоъгълник).Дефинирате финалния детайл от CadQuery като друг 2D полигон.Изваждате детайла от заготовката (Shapely метод: stock.difference(part)), за да получите полигона на материала, който трябва да бъде премахнат.Правите хоризонтални линии (проходи) през определена стъпка (напр. 2 мм) и пресмятате сеченията с отнемания материал.За компенсиране на ножа, просто прилагате метод part.buffer(tool_radius) – това автоматично измества траекторията навън с точния радиус на пластината.Кой път да изберем?Ако целта ви е максимална стабилност с минимално писане на сложни CAM алгоритми, най-сигурният път е Вариант 1 (CadQuery за геометрия + LinuxCNC G71/G72 за траектории). По този начин вашето разширение просто ще казва на LinuxCNC: "Ето крайния профил на детайла, моля те, обери материала на слоеве по 2 мм".Ако искате софтуерът ви да бъде напълно независим от LinuxCNC (да може да генерира готов разширен G-код ред по ред, който да се пусне на всякаква машина – напр. Mach3 или GRBL), тогава Вариант 3 (Python + Shapely с компенсация на радиуса) ще ви даде пълна свобода и чист код без остарели зависимости като LibLathe.Как ви изглежда идеята да прехвърлим тежката работа по сметките на G71 циклите на LinuxCNC? Или предпочитате софтуерът сам да генерира абсолютно всеки отделен G1 ход (ред по ред)?Отговорите на AI може да съдържат грешки. Научете повече5 сайтаcilynx/pygdk: Python G-code Development Kit - GitHubPython G-code Development Kit. A library to directly generate gcode for CNC machines based on object features without abstract des...GitHubSchildkroet/LibLathe: Python library for generating lathe paths ...Table_title: Schildkroet/LibLathe Table_content: header: | Name | Name | Last commit message | Last commit date | row: | Name: Lat...GitHubaewallin/opencamlib: open source computer aided ... - GitHub11.01.2023 г. — Introduction. OpenCAMLib (ocl) is a library for creating 3D toolpaths for CNC-machines such as mills and lathes. It is written in ...GitHubПоказване на всичкипотърси и други библиотеки дори на rust /go който да имат имплеменция на pythonИдеята ви да потърсите ядро, написано на Rust или Go, с готови Python bindings, е изключително зряла от софтуерна гледна точка. В съвременната софтуерна разработка това е „златният стандарт“ – тежката математика, изчисленията на вектори и колизии се правят от компилиран език с гарантирана памет и огромна скорост, а Python (чрез библиотека като PyO3 за Rust) се използва само като удобен интерфейс за потребителя и за интеграция с GUI-то.За съжаление, в тясната ниша на CNC струговането (Lathe/Turning CAM) няма готов, "out-of-the-box" проект на Rust/Go, който да е опакован за Python и да прави точно това, което искате. Повечето проекти (като careyi3/rustcam или парсерите като gcode crate) са ориентирани изцяло към 3D принтиране или 3-осно фрезоване.Въпреки това, съществуват мощни алтернативни библиотеки и подходи, които пасват перфектно на вашата архитектура (CadQuery + Python + QtDragon) и ще ви спестят писането на алгоритми от нулата:1. Индустриалният вариант: OpenCAMLib (ocl)OpenCAMLib е алгоритмичното сърце на FreeCAD. Тя е написана на C++, но има официални, изключително стабилни Python bindings.Как решава проблема ви: Тя съдържа вградени алгоритми за изчисляване на допира на режещ инструмент до 3D/2D повърхнини (т.нар. Drop-cutter и Push-cutter алгоритми).Приложение за струг: Тъй като поддържа дефиниране на конични и сферични фрези, вие можете математически да дефинирате режещата пластина на стругарския нож (напр. ромб с \(R=0.4\) мм заобляне на върха). Подавате 2D контура от CadQuery на OpenCAMLib и тя ви връща перфектно изчислена траектория с автоматична компенсация на радиуса на ножа, предпазвайки от подрязване (undercutting).2. Вариантът с Rust: Написване на собствено микро-ядро с PyO3 + geo crateАко искате да имате абсолютно чист, модерен и бърз код на Rust, който да извиквате в Python, най-добрият подход е сами да капсулирате математиката. Тъй като струговането е чисто 2D геометрия (в равнината X-Z), логиката не е толкова сложна, ако използвате правилните инструменти:В Rust използвате пакета geo (Rust ISO/OGC Geometry). Той е еквивалентът на геометрията в CadQuery, но работи със светкавична скорост.Чрез PyO3 (библиотеката за връзка между Rust и Python) правите така, че вашият Python UI да подава масив от точки (профила от CadQuery) на Rust.Логиката в Rust:Използвате функцията .buffer(radius) от Rust geo пакета върху профила на детайла. Това автоматично измества траекторията навън с точния радиус на ножа (Tool Nose Radius Compensation).Rust изчислява пресечните точки между суровата заготовка (stock) и финалния детайл, за да раздели отнемането на материала на хоризонтални проходи (напр. по 2 мм).Rust връща чист G-код текст обратно към Python.Благодарение на инструмента Maturin, компилирането на този Rust код в готов Python пакет, който инсталирате с pip install, отнема броени минути.3. Алтернативата на CadQuery: pymeam (Малко известна, но мощна)Ако установите, че CadQuery е твърде тежка (тъй като тя изисква OpenCASCADE ядрото, което е стотици мегабайти), има една специализирана Python библиотека, наречена pyacam (и производните ѝ скриптове за процедурен G-код). Тя е насочена точно към генериране на траектории чрез математически описани функции.Архитектурен съвет: Къде да инвестирате времето си?Тъй като целта ви е да изградите практично разширение за вашата машина, а не да прекарвате месеци в писане на геометрични алгоритми, най-ефективната комбинация за вашия плъгин в QtDragon е:Геометрия (Плъгини за форми): Остава в CadQuery (лесно правите цилиндри, фаски и закръгления с кодови методи).Генератор на пътя (CAM): Използвайте комбинацията от Python + Shapely (Python библиотека за 2D геометрия, написана на C). С Shapely можете да направите офсет на контура за ножа само с един ред: offset_profile = profile.buffer(tool_radius). Математиката за грубите проходи се свежда до обикновено изваждане на полигони (stock.difference(part)).Ако искате, можем да скицираме чист математически алгоритъм в Python (използващ Shapely), който да покаже как точно се взема профил от точки, как се прави отместване за радиуса на ножа и как се разделя на проходи за грубо струговане. Искате ли да пробваме това?Отговорите на AI може да съдържат грешки. Научете повече6 сайтаcareyi3/rustcam: Tools for generating G-CODE with Rust - GitHubWelcome! This is the RustCAM library and app. This app and library are intended to be a set of tools for programmatically generati...GitHubPractical Python/Rust: Building and Maintaining Dual ...5.10.2025 г. — 🔊 Recorded at PyCon DE & PyData 2025, April 25, 2025 https://2025.pycon.de/... 🎓 The presentation demonstrates how to build effi...30:49YouTube·PyCon DEgcode - Rust - Docs.rsG-code is modelled as a sequence of blocks. A Program (from parse ) is the root: it has blocks . Each Block corresponds roughly to...Docs.rsПоказване на всичкиима ли писто python алтернатива на ShapelyДа, има няколко отлични алтернативи на Shapely за изчисляване на 2D геометрия в Python. Когато изграждате CAM ядро обаче, трябва да изберете инструмент, който е математически стабилен при сложни геометрии (избягване на грешки от плаваща запетая при офсет на линии) и има висока производителност.Ето най-добрите алтернативи, разделени по технологичен стек:1. Категоричният софтуерен наследник: PyGEOS (Вече интегриран в Shapely v2.0+)Ако сте чели стари оплаквания във форумите, че Shapely е бавна библиотека, това се дължеше на старата ѝ архитектура (версии 1.x), където прехвърлянето на данни между Python и C++ енджина (GEOS) ставаше обект по обект.Какво се промени: Проектът PyGEOS разработи изцяло нови, векторизирани C-операции за Python. Тъй като беше изключително бърз, Shapely напълно погълна PyGEOS.За вашия CAM: Настоящата версия Shapely 2.x работи със скоростта на чист C. Ако я използвате правилно чрез масиви (Numpy arrays) и вграденото бързо индексиране STRtree, тя ще пресмята стотици стругови проходи за части от секундата.2. За софтуерна чистота: Clipper (Пакетът pyclipper)Ако търсите алтернатива, която е индустриален стандарт в CNC света, това е Clipper (Python bindings за C++ библиотеката Clipper на Angus Johnson).Защо е перфектна за струг: Библиотеката Clipper е създадена специално за Offsetting (изместване на контури за компенсиране на инструмент) и Boolean operations (изрязване и застъпване на полигони). Тя се използва в редица 3D принтер слайсери (като Cura) и CAM програми за изчисляване на траектории.Математическа стабилност: За разлика от Shapely, Clipper работи изцяло с цели числа (Integers) на заден план (интерполира плаващата запетая към фиксирана координатна мрежа). Това гарантира, че алгоритъмът ви никога няма да забие или да се срине заради неочаквана математическа безкрайност при допир на две перпендикулярни линии.Пример за офсет на нож с pyclipper:pythonimport pyclipper

co = pyclipper.PyclipperOffset()
# Подаваме 2D профила на детайла от CadQuery
co.AddPath(((0, 0), (100, 0), (100, 50), (120, 50)), pyclipper.JT_ROUND, pyclipper.ET_OPENROUND)

# Правим офсет (разстояние равен на радиуса на ножа, напр. 0.4 мм * коефициент на мащаб)
tool_radius = 400  # Пример с мащабиране към цели числа
solution = co.Execute(tool_radius)
Използвайте кода внимателно.3. Индустриалният "тежък" клас: scikit-geometry (CGAL Python Bindings)Ако искате софтуер без компромиси, базиран на най-мощното изчислително геометрично ядро в света – CGAL (Computational Geometry Algorithms Library), неговото Python съответствие се казва scikit-geometry.Предимство: Поддържа т.нар. Straight Skeletons и перфектни алгоритми за траектории без никакви геометрични артефакти.Минус: Много трудна за компилиране и инсталация под някои дистрибуции на Linux, докато pyclipper и shapely се инсталират с един ред.Моят съвет за вашия проектЗа да постигнете бърза скорост, лесна инсталация в LinuxCNC и нулев риск от софтуерни бъгове при изчисляване на проходите за рязане, изградете математическото си ядро върху pyclipper. Повечето софтуерни инженери, които пишат open-source CAM инструменти, избират именно нея заради безкомпромисното поведение на целите числа при изчисляване на отнемането на материал.Кой от двата подхода за дефиниране на контура ви се струва по-лесен за вашите плъгини: работата с полигони (цели числа с Clipper) или работата с чисти вектори и координати (Shapely)?Отговорите на AI може да съдържат грешки. Научете повече5 сайтаLooking for a sympy.geometry lightweight alternative : r/Python28.08.2015 г. — Such a thing does not exist as far as I know. I do a lot of geometry work. Simple geometric packages exist in abundance but invari...Reddit·r/PythonHow to Efficiently use Shapely in Python for spatial operations ...8.09.2024 г. — Get Luke Lashley's stories in your inbox. Join Medium for free to get updates from this writer. Instead of doing. point.x. Do: get...Medium·Luke LashleyMaking performant Python bindings to compiled code7.10.2025 г. — Vectorization. One of the most common places of Python overhead is in a for loop. It follows, then, that one of the easiest places...Kyle BarronПоказване на всичкиlinuxcnc използва ли готови библиотеки за изчисляване на G71 / G72: Цикли за грубо надлъжно и челно струговане (Roughing Cycles).G70: Цикъл за финишно оформяне (Finishing Cycle).G41 / G42: Автоматична хардуерна компенсация на радиуса на ножа (G42 за заден нож, G41 за преден).
или има собствен енджинLinuxCNC използва свой собствен, изключително мощен и дълбоко интегриран енджин (Interpreter) за управление на всички тези процеси. Той не разчита на външни графични или CAM библиотеки за пресмятането им на заден план.Архитектурата на LinuxCNC е изградена около ядрото RS274NGC (промишленият стандарт за G-код интерпретатори), написано на C++. Начинът обаче, по който се справя с G41/G42 и G70/G71/G72, е коренно различен и това е критично за вашия проект:1. Компенсацията на радиуса (G41 / G42) – Чист C++ енджинТова е една от най-старите и комплексни математически части в ядрото на LinuxCNC.Как работи: Когато заредите G-код с G41 или G42, C++ интерпретаторът чете кода ред по ред, но „гледа“ няколко реда напред (Look-Ahead). Той взема радиуса на ножа и ориентацията му (Tool Orientation 1-9) директно от текущия ред в таблицата с инструменти на машината (tool.tbl).Математика: Енджинът динамично изчислява допирателните вектори между кръга (върха на ножа) и дефинираните линии/дъги. Ако профилът съдържа остър вътрешен ъгъл, в който ножът физически не може да влезе, ядрото на LinuxCNC ще спре машината и ще изведе хардуерна грешка.2. Циклите за струговане (G70 / G71 / G72) – Python Remap ЕнджинТук историята е изключително интересна и важна за вашата идея с CadQuery. Години наред LinuxCNC нямаше поддръжка за G71. Тя беше добавена в по-новите версии (LinuxCNC 2.9 и нагоре) чрез механизъм, наречен Python Remapping.Как работи: Когато LinuxCNC срещне G71 в кода, вграденият C++ интерпретатор временно спира и прехвърля управлението на вграден Python скрипт (намиращ се в системните папки на LinuxCNC под името remap.py).Алгоритъмът: Този вграден Python скрипт прочита номера на подпрограмата (P аргумента), която описва финалния профил. Скриптът математически разделя този профил на хоризонтални слоеве (базирайки се на дълбочината D) и генерира виртуални G1 и G0 движения в реално време, които връща обратно към C++ нишката на машината.Огромният капан при комбинирането на G71 и G41/G42Ако решите да прехвърлите работата на LinuxCNC енджина, ще се сблъскате с проблем, който мъчи CNC инженерите в индустрията от десетилетия (включително при големи марки като Fanuc и Haas):LinuxCNC НЕ МОЖЕ да изпълнява хардуерна компенсация G41/G42 ВЪТРЕ в цикъла за грубо отнемане G71.Ако в подпрограмата на вашия профил има активиран G42 и я извикате чрез G71, LinuxCNC или ще влезе в безкраен цикъл (софтуерен бъг), или ще изведе съобщение за грешка от сорта на “Cutter compensation cannot be used with G71”.Компенсацията се активира САМО по време на финишния проход с G70. Това означава, че по време на грубото отнемане на материала (G71), машината стърже без да знае колко е голям върхът на ножа ви (приема, че е идеален остър връх с радиус 0). Това оставя неравномерно количество материал за финишния проход.Извод за вашата софтуерна архитектураТова поведение на вътрешния енджин на LinuxCNC доказва, че първоначалният ви план е много по-правилен:Ако оставите CadQuery + вашето Python CAM ядро (напр. с Clipper) да пресметнат траекторията, вие ще можете:Да направите математически перфектен офсет на профила за грубото рязане още в софтуера.Да изкарате чист, разгънат G1/G2/G3 код, в който няма скрити canned cycles.Този код ще се визуализира перфектно в QtDragon в реално време, защото интерфейсът ще вижда пълната траектория на ножа предварително, а няма да чака LinuxCNC да я пресмята динамично по време на пускане.Искате ли да разгледаме как точно се дефинира профил на детайл в CadQuery и по какъв начин можем да "извадим" 2D координатите му като чист списък от (X, Z) точки?Отговорите на AI може да съдържат грешки. Научете повече10 сайтаG-Codes - LinuxCNC9.04.2026 г. — G-Codes. ... A real value may be: * An explicit number, 4. * An expression, [2+2] * A parameter value, #88. * A unary function val...LinuxCNCG41/G42 comp for G70 cycle ? | Practical Machinist28.11.2018 г. — On newer Fanuc CNC's this is a no-no, except for G70 where you'd turn it on before the cycle.Practical MachinistWhere to adjust diameter compensation in LinuxCNC?28.11.2024 г. — Yes, this machine runs Linuxcnc with a 7i96s. I calibrated it pretty well, it keeps up tolerances nicely when I run a program gene...Facebook·LinuxCNC usersПоказване на всичкиCadQuery с Clipper. мисля че най логично да имам допълнителен бутон в linuxcnc  чрез който да се зарежда самостоятелен екран на едитора, като не блокирам работа на linuxcnc  докато създавам нов детайл, като новият детал да може и да се записва като кад детайл и като г-код детайл , след което при спряна машина да имам бърз начин на зареждане на последните генерирани детайлиТози софтуерен модел е перфектен от гледна точка на UX (потребителско изживяване) и ергономия в цеха. Разделянето на CAM редактора в самостоятелен прозорец (процес), вместо вграждането му като фиксиран таб, решава няколко критични проблема едновременно:Мултитаскинг без риск: Докато машината изпълнява дълга програма (стругова детайл), операторът може да седне на същия екран, да отвори редактора, да конфигурира следващия детайл и да го запише, без това да влияе на реалното време (Real-Time нишката) на LinuxCNC.Изолация от сривове (Crash Protection): CadQuery и Clipper изискват процесорна мощност при изчисленията. Ако се случи неочаквана софтуерна грешка в CAM редактора, той просто ще се затвори, без да срине основното управление на LinuxCNC, което би било опасно, ако машината се движи в този момент.Ето как технически се реализира тази архитектура в LinuxCNC + QtDragon и как се управлява цикълът на запис и бързо зареждане:1. Как се стартира като самостоятелен екран от LinuxCNCВ интерфейса на QtDragon (чрез Qt Designer) или директно в конфигурационните файлове добавяте потребителски бутон (например в секцията за бързи инструменти). Когато бутонът се натисне, той не просто превключва таб, а стартира вашия Python CAM софтуер като напълно отделен OS процес (Subprocess).В драйвера на QtDragon кодът за бутона изглежда така:pythonimport subprocess

def on_cam_button_clicked(self):
    # Стартира редактора като напълно независим процес
    subprocess.Popen(["python3", "/home/cnc/my_dialog_cam/main.py"])
Използвайте кода внимателно.2. Структура на файловия формат (Запис на CAD и G-code)За да може един детайл да се редактира в бъдеще, вие трябва да записвате два или три отделни файла в споделена папка (например ~/linuxcnc/nc_files/dialog_parts/):.json файл (CAD/Параметричният модел): Тъй като CadQuery изгражда модела процедурно, вие няма нужда да записвате тежки STEP файлове за редактора. Записвате само "рецептата" (списъка с операции и размери).Пример за съдържание на shaft_v1.json:json{
  "stock": {"D": 50, "L": 100},
  "tool": {"id": 2, "radius": 0.4},
  "steps": [
    {"type": "cylinder", "D": 40, "L": 30},
    {"type": "chamfer", "size": 2.0},
    {"type": "cylinder", "D": 25, "L": 50}
  ]
}
Използвайте кода внимателно..ngc или .gcode файл (Машинният код): Това е чистият G-код, изчислен от Clipper на база JSON рецептата, готов за четене от LinuxCNC.Когато операторът натисне "Запиши детайл", програмата записва едновременно part1.json (за бъдещи промени в редактора) и part1.ngc (за машината).3. Бързо зареждане при спряна машина (Връзка към LinuxCNC)Когато детайлът е готов и записан от CAM редактора, в долната част на неговия екран има голям бутон "Изпрати към машината". За да бъде операцията безопасна, вашият CAM софтуер трябва да провери състоянието на LinuxCNC, преди да инжектира кода.Тук използваме изолирания драйвер, за който говорихме по-рано, добавяйки проверка за състоянието:pythonimport linuxcnc

class LinuxCNCLoader:
    def __init__(self):
        self.command = linuxcnc.command()
        self.stat = linuxcnc.stat()

    def load_generated_gcode(self, filepath):
        # 1. Опресняваме информацията от машината
        self.stat.poll()
        
        # 2. ПРОВЕРКА ЗА БЕЗОПАСНОСТ: Машината трябва да е в състояние IDLE (спряна)
        # Не трябва да е в режим на изпълнение (TASK_STATE_ESTOP или изпълнение на код)
        if self.stat.state == linuxcnc.STATE_ESTOP:
            return "Грешка: Машината е в Авариен стоп (E-Stop)!"
            
        if self.stat.interp_state != linuxcnc.INTERP_IDLE:
            return "Грешка: Машината в момента работи или е на пауза!"

        # 3. Ако всичко е наред, зареждаме файла в QtDragon
        self.command.mode(linuxcnc.MODE_AUTO) # Превключва в автоматичен режим
        self.command.program_open(filepath)   # Зарежда G-кода на главния екран
        return "Успешно зареден детайл!"
Използвайте кода внимателно.4. Списък с последно генерирани детайли (Recent Files)За да има операторът "бърз начин на зареждане", в самия интерфейс на QtDragon или в началния екран на CAM редактора можете да изградите малък списък, който сканира папката dialog_parts/.Той просто сортира файловете по време на последна промяна (Modification Time) и показва най-новите 5 детайла:pythonimport os
import glob

def get_recent_parts(directory="~/linuxcnc/nc_files/dialog_parts"):
    path = os.path.expanduser(directory)
    # Вземаме всички JSON параметрични модели
    files = glob.glob(os.path.join(path, "*.json"))
    # Сортираме ги по дата на промяна (най-новите първи)
    files.sort(key=os.path.getmtime, reverse=True)
    
    recent_names = [os.path.basename(f).replace(".json", "") for f in files[:5]]
    return recent_names # Връща списък с имена за бутоните на екрана
Използвайте кода внимателно.Как ще изглежда работата пред машината с този модел:Машината стругова първата партида детайли.През това време операторът натиска бутона в QtDragon, отваря се CAM прозорецът на преден план.Той си конфигурира новия болт/фланец, вижда 3D/2D симулацията (пресметната от CadQuery и Clipper) и натиска "Запиши като: bolt_v2".Когато първата партида на струга приключи и машината застане в IDLE, операторът просто натиска бутона "Зареди bolt_v2" от списъка с последни детайли. Редакторът се затваря, а G-кодът вече е зареден в QtDragon, готов за натискане на Cycle Start.Искате ли да започнем с архитектурата на JSON рецептата и CadQuery генератора? Можем да напишем Python функция, която взема този JSON формат и чрез CadQuery изгражда съответния 3D модел, готов за Clipper офсет. По този начин ще имаме работещо математическо ядро.Отговорите на AI може да съдържат грешки. Научете повечев кад файла трябва да се записва и избран нож, смяна на нож, json  да е по скоро нож_номер: операции, нож_номер:операции;Това е много по-правилна индустриална логика. Вместо просто да описваме детайла като една обща геометрична форма, ние го разделяме на технологични преходи (Operations по инструменти).В реалното производство един детайл се прави с няколко ножа (например: Нож 1 за челно и грубо струговане, Нож 2 за финишно оформяне на контура, Нож 3 за изрязване/канал). Когато структурираме JSON файла по този начин, CAM ядрото автоматично ще знае кога да инжектира T1 M6, T2 M6 и т.н. в G-кода, като за всяка група операции ще пресмята офсета в Clipper с правилния радиус на пластината.Ето как трябва да изглежда структурата на параметричния JSON файл и базовият CadQuery/Clipper процесор за него:1. Архитектура на параметричния файл (part_recipe.json)json{
  "part_name": "Параметричен вал v1",
  "stock": {
    "diameter": 60.0,
    "length": 120.0,
    "material": "Steel_45"
  },
  "tool_sequences": {
    "tool_1": {
      "tool_id": 1,
      "tool_type": "Roughing_Left",
      "nose_radius": 0.8,
      "feed_rate": 0.25,
      "spindle_speed": 900,
      "operations": [
        {"type": "face", "start_z": 0.0, "depth": 2.0},
        {"type": "rough_turn", "target_d": 40.0, "start_z": 0.0, "end_z": -50.0, "step_down": 2.0}
      ]
    },
    "tool_2": {
      "tool_id": 3,
      "tool_type": "Finishing_Left",
      "nose_radius": 0.4,
      "feed_rate": 0.1,
      "spindle_speed": 1400,
      "operations": [
        {"type": "finish_profile", "start_d": 40.0, "end_d": 50.0, "length": 30.0, "chamfer": 2.0},
        {"type": "fillet", "radius": 3.0, "at_z": -30.0}
      ]
    },
    "tool_3": {
      "tool_id": 5,
      "tool_type": "Parting_Off",
      "blade_width": 3.0,
      "feed_rate": 0.08,
      "spindle_speed": 500,
      "operations": [
        {"type": "cut_off", "at_z": -80.0}
      ]
    }
  }
}
Използвайте кода внимателно.2. Как CadQuery и Clipper ще обработват тази структураКогато този файл се зареди в самостоятелния екран на вашия редактор, Python ядрото ще чете tool_sequences подред.Зареждане на Инструмента: Преди да започне да смята геометрията на операциите в дадена група, алгоритъмът прочита nose_radius (напр. 0.8 за грубия нож).CadQuery Симулация и 2D Профил: CadQuery изгражда 3D/2D модела стъпка по стъпка, изпълнявайки операциите от текущия инструмент върху заготовката (stock). Накрая извличаме 2D полигона на материала, който трябва да се отнеме.Clipper Офсет и Траектория: Подаваме този 2D полигон на Clipper. Clipper прави вътрешен/външен офсет, равен на nose_radius на текущия нож, и разделя траекторията на проходи на база step_down (дълбочина на рязане).Генериране на G-код блока: В текстовия файл се записва:Команда за смяна: T1 M6Режим на обороти и охлаждане: S900 M3 M8Траекторията от Clipper с подаване F0.25Следващият нож: T3 M6 и т.н.3. Пример за обработка на JSON структурата в PythonЕто прототип на CAM генератора, който обработва подредените по инструменти операции:python# cam_processor.py
import json
import pyclipper
# import cadquery as cq  <- тук ще е CadQuery интеграцията в реалния софтуер

class DialogCamProcessor:
    def __init__(self, json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.recipe = json.load(f)
            
    def generate_gcode(self) -> str:
        gcode_lines = []
        # Начална шапка на G-кода за LinuxCNC струг
        gcode_lines.append("G21 G18 G90 G40 G95 (Милиметри, ХZ Равнина, Подаване/Оборот)")
        
        # Сканираме последователността от ножове
        for tool_key, tool_data in self.recipe["tool_sequences"].items():
            gcode_lines.append(f"\n(--- НАЧАЛО НА ОПЕРАЦИИ С {tool_key.upper()} ---)")
            
            # 1. Инжектиране на команди за смяна на инструмент и режими
            t_num = tool_data["tool_id"]
            speed = tool_data["spindle_speed"]
            feed = tool_data["feed_rate"]
            radius = tool_data["nose_radius"]
            
            gcode_lines.append(f"T{t_num} M6 (Смяна към нож №{t_num})")
            gcode_lines.append(f"S{speed} M3 G96 D2500 (Постоянна скорост на рязане, таван 2500 об/мин)")
            gcode_lines.append("M8 (Охлаждане ВКЛ)")
            
            # 2. Обработка на операциите, зачислени към този конкретен нож
            for op in tool_data["operations"]:
                gcode_lines.append(f"(-- Операция: {op['type']} --)")
                
                # ТУК: CadQuery изгражда формата на операцията 'op'
                # ТУК: Clipper взема получената 2D линия и прави офсет с 'radius'
                
                # Примерно симулирано движение (Clipper изчислени точки)
                if op['type'] == 'rough_turn':
                    # Симулация на проходи за грубо отнемане
                    gcode_lines.append(f"G00 X{self.recipe['stock']['diameter'] + 2} Z2.0")
                    gcode_lines.append(f"G01 Z{op['end_z']} F{feed}")
                    gcode_lines.append(f"G01 X{op['target_d']}")
                    gcode_lines.append("G00 Z2.0")
                    
            gcode_lines.append("M9 (Охлаждане ИЗКЛ)")
            
        gcode_lines.append("\nM30 (Край на програмата)")
        return "\n".join(gcode_lines)

# Тест на мениджъра в симулационен режим
if __name__ == "__main__":
    # В реалния софтуер това ще прочете записания JSON от вашия UI едитор
    processor = DialogCamProcessor("part_recipe.json")
    ready_gcode = processor.generate_gcode()
    print(ready_gcode)
Използвайте кода внимателно.Предимства на този подход за вашия едитор (GUI):Когато операторът изгражда детайла на екрана, левият панел на софтуера ще показва дървовидна структура:[Tool 1 - Roughing]↳ Face Turn↳ Rough Step 1[Tool 2 - Finishing]↳ Finish Contour (Chamfer + Fillet)Той ще може лесно да хване с мишката дадена операция (например Rough Step 1) и да я премести от Tool 1 към Tool 2, или да промени реда им, като JSON структурата автоматично ще се преподреди на заден план.Искате ли да проектираме структурата на интерфейса (Layout-а в PyQt5 за QtDragon), показващ как ще се добавят тези инструменти и операции визуално, или искате първо да завържем CadQuery кода, който превръща тези операции в 3D геометрия?Отговорите на AI може да съдържат грешки. Научете повечемисля че операцията трабва да се записва и в зависимост дали е вътрешна или външна ( посоката на дълбане ), трябва да имаме и геометръ билдър за дефиниране на ножове, liblathe използва добера идея за разделяне на ножовете съобразно даташитовете и именуването, но трябва да има възможност за гуи за дефиниране на специфични ножове и библиотеки от ножове ( да речем специфични за митсубиши велер, сандвик ... )Разделянето на операциите на вътрешни (Internal / Boring) и външни (External / Turning), комбинирано с геометричен редактор на ножове, базиран на индустриалните каталози, вдига софтуера ви на професионално ниво.Посоката на рязане и подходът на ножа определят математическото поведение на Clipper. При външно струговане материалът се отнема от по-голям към по-малък диаметър (надолу към оста Z), докато при вътрешно (разстъргване) ножът влиза в предварително пробития отвор и разширява диаметъра (нагоре, отдалечавайки се от оста Z).Ето как технически и логически трябва да се имплементират тези два модула във вашия самостоятелен Python CAM редактор за LinuxCNC:1. Модул „Посока на операцията“ в JSON и ClipperВъв всяка операция се въвежда задължителен флаг "direction": "external" или "internal". Това определя как Clipper ще пресмята полигоните:Външно (External): Полигон_за_рязане = Заготовка.difference(Детайл). Clipper прави проходите от външния диаметър на заготовката надолу до контура на детайла.Вътрешно (Internal): Полигон_за_рязане = Текущ_Отвор.difference(Детайл). Clipper прави проходите от вътрешния диаметър на отвора нагоре към стената на детайла.Пример в JSON структурата:json{"type": "rough_turn", "direction": "external", "target_d": 40.0, "step_down": 2.0},
{"type": "boring", "direction": "internal", "target_d": 20.0, "step_down": 1.0}
Използвайте кода внимателно.2. Геометричен Билдър за Ножове (По метода на LibLathe и ISO 1832)Идеята на LibLathe беше добра, защото се опитваше да следва ISO 1832 стандарта за сменяеми твърдосплавни пластини. За да поддържате реални инструменти от световни лидери като Sandvik Coromant, Mitsubishi Materials и Walter Tools, вашият GUI трябва да генерира ножа чрез сглобяване на два компонента: Пластина (Insert) и Държач (Holder).Вместо потребителят да чертае сложни 3D форми, вие правите параметричен GUI с падащи менюта, базиран на ISO номенклатурата:А. Дефиниране на Пластината (Пример: CNMG 120408)Потребителят избира от стандартни опции в GUI:Форма (Позиция 1): C (Ромб 80°), W (Тригон 80°), D (Ромб 55°), T (Триъгълник 60°), V (Ромб 35°), R (Кръг). Всяка буква в кода ви дефинира математическия ъгъл на пластината.Заден ъгъл (Позиция 2): N (0°), C (7°), P (11°). Важно за проверка за колизии при задно подрязване.Размер / Дължина на ръба (Позиция 5): напр. 12 (12.7 мм).Радиус на върха (Позиция 7): 04 (0.4 мм), 08 (0.8 мм), 12 (1.2 мм). Това е стойността, която Clipper използва директно за .buffer(radius) офсета.Б. Дефиниране на Държача (Пример: PCLNR 2525M12)Начин на затягане (Позиция 1): P (Лост), S (Винт).Форма на пластината (Позиция 2): C (Трябва да съвпада с пластината).Подходен ъгъл / Стил (Позиция 3): L (95°), A (90°), D (45°). Това определя под какъв ъгъл спрямо детайла стои ножът и е критично за CadQuery симулацията на колизии.Посока (Позиция 4): R (Десен нож – реже към шпиндела), L (Ляв нож), N (Неутрален).Размер на опашката: 2525 (Квадрат 25х25 мм).3. Примерна реализация на GUI за Библиотека с Ножове в PyQt5В самостоятелния екран на вашия софтуер създавате диалогов прозорец "Мениджър на инструменти" (Tool Library). Той чете и записва база данни (например в tools_library.json).python# tool_builder_gui.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton

class ToolBuilderDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Параметричен инженерен нож (ISO 1832)")
        self.layout = QVBoxLayout(self)
        
        # 1. Избор на Производител (Mitsubishi, Sandvik, Walter...)
        self.layout.addWidget(QLabel("Производител / Каталог:"))
        self.brand_combo = QComboBox()
        self.brand_combo.addItems(["Sandvik Coromant", "Mitsubishi Materials", "Walter Tools", "Custom"])
        self.layout.addWidget(self.brand_combo)

        # 2. Избор на Форма на пластината (ISO Позиция 1)
        self.layout.addWidget(QLabel("Форма на пластината (Insert Shape):"))
        self.shape_combo = QComboBox()
        # Подаваме кода и реалния ъгъл на пластината като userData
        self.shape_combo.addItem("C - Ромб 80°", 80)
        self.shape_combo.addItem("D - Ромб 55°", 55)
        self.shape_combo.addItem("T - Триъгълник 60°", 60)
        self.shape_combo.addItem("V - Ромб 35° (Финишен)", 35)
        self.layout.addWidget(self.shape_combo)
        
        # 3. Избор на Радиус на ножа (ISO Позиция 7)
        self.layout.addWidget(QLabel("Радиус на върха (Nose Radius R):"))
        self.radius_combo = QComboBox()
        self.radius_combo.addItem("04 (0.4 mm)", 0.4)
        self.radius_combo.addItem("08 (0.8 mm)", 0.8)
        self.radius_combo.addItem("12 (1.2 mm)", 1.2)
        self.layout.addWidget(self.radius_combo)
        
        # 4. Ориентация/Посока на рязане
        self.layout.addWidget(QLabel("Тип операция за ножа:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Външно струговане (Turning)", "Вътрешно разстъргване (Boring Bar)", "Канал/Отрязване"])
        self.layout.addWidget(self.type_combo)

        # Бутон за запис в библиотеката
        self.btn_save = QPushButton("Запиши в Tool Table на LinuxCNC")
        self.btn_save.clicked.connect(self.save_tool)
        self.layout.addWidget(self.btn_save)

    def save_tool(self):
        # Вземане на математическите параметри за Clipper и CadQuery
        chosen_radius = self.radius_combo.currentData()
        chosen_angle = self.shape_combo.currentData()
        tool_type = self.type_combo.currentText()
        brand = self.brand_combo.currentText()
        
        # Тук данните се записват в JSON библиотеката на вашия софтуер
        # и автоматично форматират ред за системната таблица на LinuxCNC tool.tbl
        print(f"Записан нож: {brand}, Радиус: {chosen_radius}mm, Основен ъгъл: {chosen_angle}°, Тип: {tool_type}")
        self.accept()
Използвайте кода внимателно.Как CadQuery ще чертае ножа визуалноБлагодарение на тези ISO параметри, вие можете да накарате CadQuery да начертае перфектен 2D/3D модел на самия нож на екрана на симулатора, без да имате STEP файл за него:pythonimport cadquery as cq

def build_parametric_insert(shape_letter, size, radius):
    # Математическо изчертаване на пластината в CadQuery за визуализация на екрана
    if shape_letter == 'C':  # 80 градусов ромб
        # Изчертава се ромб с вътрешен ъгъл 80 градуса, 
        # след което се прилага .fillet(radius) на режещия връх
        profile = cq.Workplane("XZ").rect(size, size).toPending() # опростен пример
        # ... реална векторизация на ISO ромба ...
        return profile
Използвайте кода внимателно.Защо този подход елиминира нуждата от външни CAD файлове за ножовете?Когато операторът избере от списъка "Sandvik CNMG 120408", вашето ядро веднага знае:За Clipper: Трябва да направи отместване на траекторията точно с 0.8 мм.За Посоката: Ако операцията е маркирана като "internal", а ножът е дефиниран като "Външно струговане", софтуерът веднага ще изведе визуално предупреждение на екрана: "Грешка: Избран е външен нож за вътрешна операция (Опасност от сблъсък)!".Искате ли да интегрираме Clipper алгоритъма за вътрешно спрямо външно рязане, за да видите как се разделят проходите в зависимост от посоката на дълбане?Отговорите на AI може да съдържат грешки. Научете повече5 сайтаCutting tool assembly creation and management softwareSimplify and optimize your tool selection * Comprehensive cloud tool library with accurate and up-to-date data. * Save time, reduc...Sandvik CoromantDesignation key in accordance with ISO 1832 ... - Walter ToolsDesignation key in accordance with ISO 1832 for indexable inserts for turning. 6. Insert thickness s. [mm]. 01 s = 1,59. T1 s = 1,Walter ToolsISO Inserts - Nomenclature, Dimensions & Tolerances15.06.2024 г. — Turning Inserts Nomenclature- charts (ISO & ANSI) The designation of ISO inserts is described in ISO 1832 (and in ANSI B212. 12. *Machining DoctorПоказване на всичкитъй като използваме субпроцес, вече не зме зависими от linuxcnc gui, можем с добавяне на един бутон да показваме нов прозорец на едитора ни  , също така можем да преминем от PyQt5 към PyQt6 или PySide6Преминаването към PySide6 (официалната библиотека от създателите на Qt) или PyQt6 е отлично софтуерно решение. Тъй като стартирате софтуера като напълно самостоятелен операционен процес (subprocess), вие разбивате всички окови и зависимости от по-старата графична архитектура на LinuxCNC (която все още разчита масово на PyQt5/Qt5 в стабилните си версии).Тази стъпка дава на проекта ви огромни технологични предимства:Предимствата на PySide6 / PyQt6 във вашия случайМодерен CadQuery Преглед: Модерните 3D визуализатори за Python (като pyvista или OCP.vtk, които се използват за рендериране на CadQuery/OpenCASCADE геометрия в реално време) имат много по-стабилна поддръжка и по-висока производителност под Qt6.Пълна съвместимост с Wayland: Модерните Linux дистрибуции бързо заменят старата графична система X11 с Wayland. Qt6 има native поддръжка за Wayland, което означава, че интерфейсът на вашия едитор ще се мащабира перфектно на тъчскрийн екрани, без накъсвания и графични артефакти.Софтуерно дълголетие: Изграждайки проекта на PySide6, вие гарантирате, че той ще бъде актуален през следващите 10 години, без да се налага пренаписване.Архитектура на стартиране: Бутон в QtDragon \(\rightarrow \) PySide6 ПрозорецЕто как се реализира мостът. Бутонът в интерфейса на машината (QtDragon - Qt5) просто извиква системна команда, която стартира вашия нов, модерен едитор (PySide6).1. Кодът вътре в драйвера на LinuxCNC (QtDragon / Qt5):python# Този код се изпълнява в контекста на LinuxCNC QtDragon
import subprocess
import os

def on_open_editor_clicked(self):
    # Пътят до изпълнимия скрипт на вашия модерен PySide6 CAM едитор
    editor_script = "/home/cnc/my_modern_cam/main.py"
    
    # Стартираме го като напълно отделен процес в операционната система
    # По този начин Qt5 интерфейсът на машината и Qt6 интерфейсът на едитора живеят в мир
    subprocess.Popen(["python3", editor_script])
Използвайте кода внимателно.2. Архитектура на самостоятелния едитор (PySide6 / Qt6):Вашият едитор вече се възползва от пълната мощ на Qt6. Той разполага с дърво на операциите (външни/вътрешни), параметричен мениджър на ножове (Mitsubishi, Sandvik и т.н.) и бутон за запис.python# main.py (Самостоятелно PySide6 Приложение)
import sys
import json
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget
from PySide6.QtCore import Qt

class ModernCamEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Параметричен Стругов CAM (PySide6 + Clipper)")
        self.resize(1024, 768)
        
        # Главен контейнер
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Ляв панел: Дърво с операции, разделени по инструменти
        left_panel = QVBoxLayout()
        self.op_list = QListWidget()
        self.op_list.addItem("[T01 - Roughing Mitsubishi] - External Turn")
        self.op_list.addItem("[T03 - Finishing Sandvik] - Chamfer & Profile")
        self.op_list.addItem("[T05 - Boring Bar Walter] - Internal Boring")
        left_panel.addWidget(self.op_list)
        
        # Десен панел: Бутони за управление и CadQuery визуализация
        right_panel = QVBoxLayout()
        
        btn_save = QPushButton("Запиши CAD (JSON) и G-code")
        btn_save.clicked.connect(self.save_and_compile)
        
        btn_send = QPushButton("Изпрати и зареди в LinuxCNC")
        btn_send.clicked.connect(self.send_to_machine)
        
        right_panel.addWidget(btn_save)
        right_panel.addWidget(btn_send)
        right_panel.addStretch() # Място за 3D/2D Canvas (CadQuery/Clipper визуализатор)
        
        # Сглобяване на интерфейса
        main_layout.addLayout(left_panel, stretch=1)
        main_layout.addLayout(right_panel, stretch=2)

    def save_and_compile(self):
        # 1. Вземаме данните от интерфейса и записваме JSON рецептата
        # 2. Clipper изчислява външните/вътрешните проходи съобразно ножовете
        # 3. Записваме готовия .ngc файл на диска
        print("Детайлът е компилиран и записан успешно.")

    def send_to_machine(self):
        # Понеже сме в отделен процес, използваме изолирания linuxcnc_driver.py,
        # за да кажем на машината безопасно да отвори генерирания файл, ако е в IDLE
        print("G-кодът е инжектиран в LinuxCNC.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Прилагане на модерен тъмен стил, подходящ за цеха
    app.setStyle('Fusion') 
    editor = ModernCamEditor()
    editor.show()
    sys.exit(app.exec())
Използвайте кода внимателно.Какво следва оттук нататък?С тази стъпка изградихме перфектната софтуерна концепция:Интерфейс на машината: QtDragon (стабилен, контролиращ хардуера).Интерфейс на CAM: Самостоятелен PySide6 прозорец (модерен, бърз, интерактивен).Данни: JSON рецепти, разделени по инструменти (Mitsubishi, Sandvik) и посока на рязане (външно/вътрешно).Математическо ядро: CadQuery за геометрия + Clipper за офсет и траектории.След като вече изчистихме софтуерната рамка и избрахме PySide6, как искате да продължим: да разпишем математическата логика в Clipper за пресмятане на вътрешния срещу външния полигон за рязане, или да дефинираме как CadQuery ще експортира чистите координати на детайла към Clipper?Отговорите на AI може да съдържат грешки. Научете повечеще бъдем и независими към избора на гуи, QtVCP, GMOCCAPY, AXIS и другиТочно така! Тази архитектурна стъпка ви дава 100% софтуерна независимост. Понеже вашият PySide6 едитор се стартира като напълно самостоятелно операционно приложение (subprocess), за него е абсолютно без значение кой графичен интерфейс (GUI) е зареден на екрана на LinuxCNC – дали ще е QtDragon (QtVCP), GMOCCAPY (GTK), класическият AXIS (TkInter) или модерният уеб-базиран Remora / WebUI.Единствената ви допирна точка с LinuxCNC остава операционната система (Linux) и ниско ниво на API комуникация за инжектиране на G-кода.За да постигнете тази абсолютна независимост, ето как трябва да реализирате финалната връзка към LinuxCNC:Универсални методи за инжектиране на G-код (Независимо от GUI-то)Когато натиснете бутона „Изпрати към машината“ във вашия PySide6 едитор, има два начина да заредите G-кода, които работят при всеки интерфейс на LinuxCNC:Вариант А: Чрез чистия linuxcnc Python модул (Най-добрият начин)Този метод комуникира директно с командното ядро (Task Executor) на LinuxCNC през споделена памет (NML канали), заобикаляйки изцяло графичния интерфейс.pythonimport linuxcnc

def universal_inject(gcode_filepath):
    try:
        # Свързваме се с ядрото на LinuxCNC
        command = linuxcnc.command()
        stat = linuxcnc.stat()
        stat.poll()
        
        # Проверяваме дали машината е свободна (IDLE)
        if stat.interp_state == linuxcnc.INTERP_IDLE:
            command.mode(linuxcnc.MODE_AUTO)
            # Тази команда казва на LinuxCNC да отвори файла. 
            # AXIS, GMOCCAPY или QtDragon ВЕДНАГА ще опреснят екраните си с новия код!
            command.program_open(gcode_filepath)
            return "Успешно зареден код!"
        else:
            return "Машината е заета в момента!"
    except Exception as e:
        return f"Грешка при връзката: {e}"
Използвайте кода внимателно.Вариант Б: Чрез LinuxCNC МДИ (MDI) команда (Алтернатива)Ако интерфейсът има рестрикции (които са рядкост), можете да инжектирате G-кода чрез извикване на системна подпрограма. Записвате кода като стандартен файл и извиквате MDI команда: M23 filename.ngc.Как ще конфигурирате бутона за стартиране в различните GUI-та?За да може операторът да отвори вашия PySide6 едитор от самата машина, вие просто добавяте бутон в съответния интерфейс, като всички те поддържат стартиране на външни програми:В AXIS: Добавя се един ред в системния ~/.axisrc файл:pythonroot_window.bind("<F12>", lambda event: subprocess.Popen(["python3", "/path/to/editor.py"]))
# Това ще отваря едитора при натискане на клавиш F12 или чрез добавяне на бутон в менюто.
Използвайте кода внимателно.В GMOCCAPY: В INI файла на машината, под секцията [DISPLAY], просто използвате вградената функция за външни бутони:ini[DISPLAY]
USER_COMMAND_BUTTON = name="Диалогов CAM"; command=python3 /path/to/editor.py
Използвайте кода внимателно.GMOCCAPY автоматично ще създаде голям, удобен за тъчскрийн бутон в долната част на екрана.В QtDragon / QtVCP: Както обсъдихме, чрез свързване на бутон в Qt Designer към subprocess.Popen().Стратегия за следващата стъпкаСега, когато софтуерната архитектура е напълно изчистена и имате абсолютна свобода по отношение на интерфейсите, е време да изградим „мозъка“ на CAM ядрото.Как искате да продължим напред:CadQuery + Clipper Математика: Да напишем Python модула, който взема заготовка (цилиндър), вади от нея 2D профила, усеща посоката (външно струговане или вътрешно разстъргване) и изчислява проходите с компенсация на радиуса на ножа?JSON структура на Библиотеката с ножове: Да дефинираме как да се записват ножовете (Sandvik/Mitsubishi) и как едиторът да ги визуализира в 2D?