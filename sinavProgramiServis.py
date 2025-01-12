#Servis haline getirilmiş hali.Altında backende göre düzenlenmiş hali var.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random
import time

# FastAPI uygulamasını başlat
app = FastAPI()

# Veri modelleri
class Sinav(BaseModel):
    ders_adi: str
    ogrenci_sayisi: int
    sinif_grubu: int
    sure: int

class Sinif(BaseModel):
    sinif_adi: str
    kapasite: int

class GunSaat(BaseModel):
    tarih: str
    baslangic_saatleri: List[str]

class PlanlamaGirdisi(BaseModel):
    sinavlar: List[Sinav]
    siniflar: List[Sinif]
    gun_saat: List[GunSaat]

# Sınav planlama algoritması
def sinav_planlama(girdi: PlanlamaGirdisi) -> Dict[str, Any]:
    maks_sinav_per_gun = 26
    maks_grup_sinavi = 2
    minimum_grup_zaman_farki = 120

    sinavlar = sorted(girdi.sinavlar, key=lambda x: -x.ogrenci_sayisi)
    siniflar = sorted(girdi.siniflar, key=lambda x: -x.kapasite)
    gun_saat = girdi.gun_saat

    grup_anahtarlari = {sinav.sinif_grubu for sinav in sinavlar}
    gun_basi_sinav_sayisi = {gun.tarih: 0 for gun in gun_saat}
    gun_basi_grup_sinavlari = {
        gun.tarih: {grup: 0 for grup in grup_anahtarlari} for gun in gun_saat
    }
    saat_durumu = {}
    planlama = []
    yerlesemeyen_sinavlar = []

    grup_sinav_zamanlari = {
        gun.tarih: {grup: [] for grup in grup_anahtarlari} for gun in gun_saat
    }

    def siniflari_karistir(siniflar):
        return random.sample(siniflar, len(siniflar))

    def grup_zaman_kontrolu(tarih, sinif_grubu, baslangic_zamani):
        for grup_baslangic in grup_sinav_zamanlari[tarih][sinif_grubu]:
            fark = abs((baslangic_zamani - grup_baslangic).total_seconds() / 60)
            if fark < minimum_grup_zaman_farki:
                return False
        return True

    def sinavi_yerlesecek_slotu_bul(sinav, gun, tarih, sinif_kullanimi):
        for baslangic in gun.baslangic_saatleri:
            baslangic_zamani = datetime.strptime(baslangic, "%H:%M")
            bitis_zamani = baslangic_zamani + timedelta(minutes=sinav.sure)

            if not grup_zaman_kontrolu(tarih, sinav.sinif_grubu, baslangic_zamani):
                continue

            sinif_musait = all(
                all(
                    not (
                        baslangic_zamani < datetime.strptime(dolu_bitis, "%H:%M") and
                        bitis_zamani > datetime.strptime(dolu_baslangic, "%H:%M")
                    )
                    for dolu_baslangic, dolu_bitis in saat_durumu.get(tarih, {}).get(sinif, [])
                )
                for sinif in sinif_kullanimi
            )

            if sinif_musait:
                return baslangic, bitis_zamani.strftime("%H:%M")
        return None, None

    gun_index = 0

    def sonraki_gun_getir():
        nonlocal gun_index
        gun_index = (gun_index + 1) % len(gun_saat)
        return gun_saat[gun_index]

    for sinav in sinavlar:
        ogrenci_sayisi = sinav.ogrenci_sayisi
        sinif_kullanimi = []

        for sinif in siniflari_karistir(siniflar):
            if ogrenci_sayisi <= 0:
                break
            if sinif.kapasite <= ogrenci_sayisi:
                sinif_kullanimi.append(sinif.sinif_adi)
                ogrenci_sayisi -= sinif.kapasite
            elif ogrenci_sayisi <= sinif.kapasite:
                sinif_kullanimi.append(sinif.sinif_adi)
                ogrenci_sayisi = 0

        yerlesim_tamamlandi = False
        for _ in range(len(gun_saat)):
            gun = sonraki_gun_getir()
            tarih = gun.tarih
            if yerlesim_tamamlandi:
                break
            if (
                gun_basi_sinav_sayisi[tarih] >= maks_sinav_per_gun or
                gun_basi_grup_sinavlari[tarih][sinav.sinif_grubu] >= maks_grup_sinavi
            ):
                continue
            baslangic, bitis = sinavi_yerlesecek_slotu_bul(sinav, gun, tarih, sinif_kullanimi)

            if baslangic and bitis:
                planlama.append({
                    "Date": tarih,
                    "StartTime": baslangic,
                    "EndTime": bitis,
                    "LectureCode": sinav.ders_adi,
                    "RoomNames": ", ".join(sinif_kullanimi),
                    "Duration (minute)": sinav.sure,
                })
                for sinif in sinif_kullanimi:
                    saat_durumu.setdefault(tarih, {}).setdefault(sinif, []).append((baslangic, bitis))
                grup_sinav_zamanlari[tarih][sinav.sinif_grubu].append(datetime.strptime(baslangic, "%H:%M"))
                gun_basi_sinav_sayisi[tarih] += 1
                gun_basi_grup_sinavlari[tarih][sinav.sinif_grubu] += 1
                yerlesim_tamamlandi = True

        if not yerlesim_tamamlandi:
            yerlesemeyen_sinavlar.append(sinav.ders_adi)

    return {"planlama": planlama, "yerlesemeyen_sinavlar": yerlesemeyen_sinavlar}

# API Endpoint
@app.post("/planlama")
def planlama_endpoint(girdi: PlanlamaGirdisi):
    try:
        sonuc = sinav_planlama(girdi)
        return sonuc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""

#Backende göre düzenlenmiş hali.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

app = FastAPI()

# Veri modelleri (ExamSessionPostDto ve ExamRoomDto'ya benzer)
class Exam(BaseModel):
    lecture_code: str
    student_count: int
    grade: int
    duration: int

class Room(BaseModel):
    room_name: str
    exam_capacity: int

class DayTime(BaseModel):
    date: str
    start_times: List[str]

class PlanningInput(BaseModel):
    exams: List[Exam]
    rooms: List[Room]
    day_time: List[DayTime]

def exam_planning(input_data: PlanningInput) -> Dict[str, Any]:
    max_exams_per_day = 26
    max_group_exam = 2
    min_group_time_diff = 120

    exams = sorted(input_data.exams, key=lambda x: -x.student_count)
    rooms = sorted(input_data.rooms, key=lambda x: -x.exam_capacity)
    day_time = input_data.day_time

    group_keys = {exam.grade for exam in exams}
    daily_exam_count = {day.date: 0 for day in day_time}
    daily_group_exams = {
        day.date: {group: 0 for group in group_keys} for day in day_time
    }
    time_status = {}
    planning = []
    unscheduled_exams = []

    group_exam_times = {
        day.date: {group: [] for group in group_keys} for day in day_time
    }
    """
    Amacı: Oda listesini karıştırarak her seferinde farklı bir oda sıralaması elde etmek.
    İşleyişi:
    random.sample fonksiyonu, verilen listeyi rastgele bir şekilde yeniden sıralar ve yeni bir liste döndürür.
    Böylece her sınav için odaların sıralaması değişir ve sınavların farklı odalarda yapılma olasılığı artar.
    """
    def shuffle_rooms(rooms):
        return random.sample(rooms, len(rooms))

    """
    Amacı: Aynı sınıf seviyesinden sınavların arasında belirli bir minimum süre farkı olup olmadığını kontrol etmek.
    İşleyişi:
    Belirli bir tarih ve sınıf seviyesi için daha önce planlanan sınavların başlangıç saatlerini kontrol eder.
    Yeni sınavın başlangıç saati ile mevcut sınavların başlangıç saatleri arasındaki süre farkını hesaplar.
    Eğer bu fark min_group_time_diff değerinden küçükse, False döner (sınav bu zaman dilimine yerleştirilemez).
    Aksi takdirde, True döner (sınav bu zaman dilimine yerleştirilebilir).
    """
    def group_time_check(date, grade, start_time):
        for group_start in group_exam_times[date][grade]:
            diff = abs((start_time - group_start).total_seconds() / 60)
            if diff < min_group_time_diff:
                return False
        return True
    """
    Amacı: Verilen sınav için uygun bir başlangıç ve bitiş saati bulmak.
    İşleyişi:
    Gün içindeki her başlangıç saati için sınavın başlangıç ve bitiş saatlerini hesaplar.
    Grup Zaman Kontrolü: group_time_check fonksiyonunu çağırarak aynı sınıf seviyesinden diğer sınavlarla zaman farkını kontrol eder.
    Oda Uygunluğu Kontrolü: Her oda için belirtilen zaman aralığında başka bir sınav olup olmadığını kontrol eder.
    Eğer tüm odalar uygun ise, sınav için başlangıç ve bitiş saatlerini döndürür.
    Uygun bir zaman bulunamazsa, (None, None) döner.
    """
    def find_exam_slot(exam, day, date, room_usage):
        for start in day.start_times:
            start_time = datetime.strptime(start, "%H:%M")
            end_time = start_time + timedelta(minutes=exam.duration)

            if not group_time_check(date, exam.grade, start_time):
                continue

            room_available = all(
                all(
                    not (
                        start_time < datetime.strptime(busy_end, "%H:%M") and
                        end_time > datetime.strptime(busy_start, "%H:%M")
                    )
                    for busy_start, busy_end in time_status.get(date, {}).get(room, [])
                )
                for room in room_usage
            )

            if room_available:
                return start, end_time.strftime("%H:%M")
        return None, None

    day_index = 0
    """
    Amacı: Sıradaki günü döndürmek ve day_index değerini güncellemek.
    İşleyişi:
    day_index değişkenini bir artırır ve mod işlemiyle gün sayısını aşmayacak şekilde sıfırlanmasını sağlar.
    Böylece günlerin döngüsel olarak sırasıyla kontrol edilmesini sağlar.
    Mevcut günün bilgisini döndürür.
    """
    def get_next_day():
        nonlocal day_index
        day_index = (day_index + 1) % len(day_time)
        return day_time[day_index]

    """
    Bu kod bölümü, sınavların odalara ve zaman dilimlerine yerleştirilmesini sağlayan ana döngüyü içerir.
    """


    """
    Sınavlar, öğrenci sayısına göre sıralı olarak ele alınır (exams listesi daha önce öğrenci sayısına göre azalan şekilde sıralandı).
    student_count: Mevcut sınavın öğrenci sayısını tutar.
    room_usage: Bu sınav için kullanılacak odaların isimlerini tutacak bir liste.
    """
    for exam in exams:
        student_count = exam.student_count
        room_usage = []
        """
        Amaç: Sınav için yeterli kapasiteye sahip odaları belirlemek.
        shuffle_rooms(rooms) ile odaların sırası rastgele karıştırılır.
        Odalar sınavın öğrenci sayısına göre yerleştirilir:
        Eğer oda kapasitesi sınavın öğrenci sayısına eşit veya küçükse, oda sınav için kullanılır ve öğrenci sayısından bu kapasite düşülür.
        Eğer kalan öğrenci sayısı bir odanın kapasitesine eşit veya daha azsa, o oda da kullanılır ve öğrenci sayısı sıfırlanır.
        """
        for room in shuffle_rooms(rooms):
            if student_count <= 0:
                break
            if room.exam_capacity <= student_count:
                room_usage.append(room.room_name)
                student_count -= room.exam_capacity
            elif student_count <= room.exam_capacity:
                room_usage.append(room.room_name)
                student_count = 0
        """
        Amaç: Sınav için uygun bir gün ve zaman dilimi bulmak.
        placement_completed sınavın yerleşiminin tamamlanıp tamamlanmadığını takip eder.
        get_next_day() ile sıradaki gün seçilir.
        Günlük sınav ve grup sınavı sınırları kontrol edilir:
        daily_exam_count[date]: O gün için maksimum sınav sayısı.
        daily_group_exams[date][exam.grade]: O gün için aynı sınıf seviyesinden maksimum sınav sayısı.
        Eğer günlük sınav veya grup sınavı sınırları aşılmışsa, bir sonraki güne geçilir (continue).
        """
        placement_completed = False
        for _ in range(len(day_time)):
            day = get_next_day()
            date = day.date
            if placement_completed:
                break
            if (
                daily_exam_count[date] >= max_exams_per_day or
                daily_group_exams[date][exam.grade] >= max_group_exam
            ):
                continue


            """
            Amaç: Uygun bir başlangıç ve bitiş saati bulmak ve sınavı yerleştirmek.
            find_exam_slot(exam, day, date, room_usage) fonksiyonu, sınavın odalar için uygun bir zaman aralığı bulur.
            Eğer uygun bir zaman bulunursa:
            Sınavın bilgileri planning listesine eklenir.
            Kullanılan odaların zaman durumu time_status'a eklenir.
            Aynı sınıf seviyesi için sınavın zamanı group_exam_times'a eklenir.
            Günlük sınav ve grup sınavı sayıları güncellenir.
            placement_completed işaretlenerek sınavın yerleştirme işlemi tamamlanır.
            """
            start, end = find_exam_slot(exam, day, date, room_usage)

            if start and end:
                planning.append({
                    "Date": date,
                    "StartTime": start,
                    "EndTime": end,
                    "LectureCode": exam.lecture_code,
                    "RoomNames": ", ".join(room_usage),
                    "Duration (minute)": exam.duration,
                })
                for room in room_usage:
                    time_status.setdefault(date, {}).setdefault(room, []).append((start, end))
                group_exam_times[date][exam.grade].append(datetime.strptime(start, "%H:%M"))
                daily_exam_count[date] += 1
                daily_group_exams[date][exam.grade] += 1
                placement_completed = True
        """
        Amaç: Eğer sınav bir güne veya zaman dilimine yerleştirilemezse, bu sınavı unscheduled_exams listesine eklemek.
        Bu liste, planlanamayan sınavların kodlarını içerir.
        """
        if not placement_completed:
            unscheduled_exams.append(exam.lecture_code)
    """
    Amaç: Planlanan sınavların ve planlanamayan sınavların listesini döndürmek.
    planning: Başarıyla planlanan sınavların detaylarını içerir.
    unscheduled_exams: Planlanamayan sınavların kodlarını içerir.
    """
    return {"planning": planning, "unscheduled_exams": unscheduled_exams}

@app.post("/planning")
def planning_endpoint(input_data: PlanningInput):
    try:
        result = exam_planning(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
