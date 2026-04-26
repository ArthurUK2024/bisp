import io
import urllib.error
import urllib.request
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import transaction as db_transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.accounts.models import User
from apps.bookings.models import Booking, BookingState, BookingStateTransition
from apps.bookings.services import calculate_booking_price, transition
from apps.catalog.models import Listing, ListingPhoto

DEMO_TAG = "[demo]"


DEMO_USERS = [
    ("aziz.karimov@ijara.demo", "Aziz Karimov", "Chilonzor", "+998 90 111 22 33"),
    ("dilnoza.tursunova@ijara.demo", "Dilnoza Tursunova", "Yunusobod", "+998 90 222 33 44"),
    ("rustam.yuldashev@ijara.demo", "Rustam Yuldashev", "Mirobod", "+998 90 333 44 55"),
    ("malika.abdullaeva@ijara.demo", "Malika Abdullaeva", "Mirzo Ulugbek", "+998 90 444 55 66"),
]

DEMO_PASSWORD = "zx7mnp45"


DEMO_LISTINGS = [
    # (title, description, category, district, price_hour, price_day, price_month, photo_count)
    (
        "Dewalt 18V cordless drill set",
        "Professional brushless drill with two 5Ah batteries, rapid charger, and a 40-piece bit set. Great for home renovation or quick repairs. Case included.",
        "tools",
        "chilonzor",
        None,
        50000,
        None,
        3,
    ),
    (
        "Bosch jigsaw with blade set",
        "Corded jigsaw for smooth precise cuts. Comes with 5 assorted blades for wood and metal. Lightweight, easy for beginners.",
        "tools",
        "yakkasaray",
        None,
        40000,
        None,
        2,
    ),
    (
        "Aluminium telescopic ladder 6m",
        "Extends up to 6m. Holds up to 120kg. Folds down to 1.2m for easy transport in a sedan. Suitable for roof work and painting.",
        "tools",
        "sergeli",
        None,
        60000,
        None,
        2,
    ),
    (
        "Sony A7 IV mirrorless camera",
        "Full-frame 33MP body with 4K video. Includes the 28-70mm kit lens, one spare battery, and a 64GB SD card. Camera bag provided.",
        "electronics",
        "mirobod",
        50000,
        250000,
        3500000,
        3,
    ),
    (
        "DJI Mini 3 Pro drone kit",
        "Under 249g so no registration needed in Uzbekistan. 48MP photo, 4K video, 34-min flights. Carry case plus 3 fully charged batteries.",
        "electronics",
        "mirzo_ulugbek",
        None,
        220000,
        None,
        3,
    ),
    (
        "Canon 600W photo studio kit",
        "Two softboxes, two light stands, one backdrop stand with two 3x2m backdrops (white and grey). Plug and shoot.",
        "electronics",
        "yunusobod",
        None,
        180000,
        None,
        2,
    ),
    (
        "Outdoor canopy tent 3x3m",
        "Waterproof canopy with four removable side walls. Ideal for small weddings, bazaar stalls, or family picnics. Packs into a wheeled bag.",
        "event_gear",
        "shaykhontohur",
        None,
        200000,
        None,
        3,
    ),
    (
        "PA speaker plus two microphones",
        "500W powered speaker with two wired microphones and mic stands. Covers up to 80 people indoors. XLR cables included.",
        "event_gear",
        "mirobod",
        None,
        250000,
        None,
        2,
    ),
    (
        "Glass-door mini fridge 60L",
        "Perfect for keeping drinks cold at an event. Silent compressor, single shelf, plugs into standard outlet.",
        "event_gear",
        "olmazor",
        None,
        120000,
        None,
        3,
    ),
    (
        "Giant Talon 3 mountain bike",
        "29er hardtail, frame size M (fits 170-180cm riders). Hydraulic disc brakes, 21-speed. Just serviced last week. Helmet included.",
        "sports",
        "yashnabad",
        15000,
        80000,
        None,
        3,
    ),
    (
        "Coleman 4-person dome tent",
        "Full rainfly, aluminium poles, pegs, and ground sheet. Pitches in 10 minutes. Weighs 4.5kg. Tested in Chimgan weekends.",
        "sports",
        "bektemir",
        None,
        90000,
        None,
        2,
    ),
    (
        "Rossignol ski set 170cm",
        "All-mountain skis, 170cm. Boots size 43 EU. Bindings adjust for 41-45 EU. Poles included. Wax fresh.",
        "sports",
        "uchtepa",
        None,
        100000,
        None,
        3,
    ),
    (
        "Folding banquet tables (set of 4)",
        "Rectangular 180cm tables, each seats 8 comfortably. Fold flat for transport. Great for home gatherings or small events.",
        "furniture",
        "sergeli",
        None,
        120000,
        None,
        2,
    ),
    (
        "Chiavari chairs, set of 20",
        "Gold-finish Chiavari chairs with ivory seat cushions. Delivery included within Tashkent city limits. Perfect for weddings.",
        "furniture",
        "chilonzor",
        None,
        250000,
        None,
        3,
    ),
    (
        "Lada Niva 2121 off-road",
        "Classic 4x4, 1.7L petrol, manual. Clean interior. Great for mountain trips and rough roads. Pickup from Mirobod, full tank.",
        "vehicles",
        "mirobod",
        None,
        600000,
        12000000,
        3,
    ),
    (
        "Xiaomi Pro 2 electric scooter",
        "45km range on a charge, folds compact. Good for commuting inside Tashkent center. Helmet and phone mount included.",
        "vehicles",
        "yakkasaray",
        20000,
        120000,
        None,
        2,
    ),
    (
        "4K projector 3000 lumens",
        "Native Full HD, accepts 4K input. Comes with a 100-inch pull-down screen and a 5m HDMI cable. Movie night ready.",
        "other",
        "yunusobod",
        None,
        180000,
        None,
        2,
    ),
    (
        "Manfrotto tripod plus DJI RS3 gimbal",
        "Manfrotto 055 tripod with fluid head, plus a DJI RS3 three-axis stabiliser with rechargeable battery. For serious video work.",
        "other",
        "mirzo_ulugbek",
        20000,
        200000,
        None,
        3,
    ),
]


class Command(BaseCommand):
    help = "Seed the database with demo users, listings, photos, and bookings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe demo rows (by email domain @ijara.demo) before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        users = [self._make_user(*row) for row in DEMO_USERS]

        created_listings = []
        for idx, row in enumerate(DEMO_LISTINGS):
            owner = users[idx % len(users)]
            listing = self._make_listing(owner, *row)
            created_listings.append(listing)

        self._make_bookings(created_listings, users)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(users)} users, {len(created_listings)} listings, bookings."
            )
        )

    def _reset(self):
        demo_users = User.objects.filter(email__endswith="@ijara.demo")
        self.stdout.write(f"Deleting {demo_users.count()} demo users and related data...")
        # BookingStateTransition.actor is PROTECT — clear bookings before users.
        Booking.objects.filter(renter__in=demo_users).delete()
        Booking.objects.filter(listing__owner__in=demo_users).delete()
        demo_users.delete()

    def _make_user(self, email, display_name, _home_district, phone):
        is_staff = email == DEMO_USERS[0][0]
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"is_active": True, "is_staff": is_staff, "is_superuser": is_staff},
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        elif user.is_staff != is_staff:
            user.is_staff = is_staff
            user.is_superuser = is_staff
            user.save(update_fields=["is_staff", "is_superuser"])
        profile = user.profile
        profile.display_name = display_name
        profile.phone = phone
        profile.bio = f"Demo user for the Ijara prototype. Lives in {_home_district}."
        profile.save()
        return user

    def _make_listing(
        self,
        owner,
        title,
        description,
        category,
        district,
        price_hour,
        price_day,
        price_month,
        photo_count,
    ):
        listing, _ = Listing.objects.get_or_create(
            owner=owner,
            title=title,
            defaults={
                "description": description,
                "category": category,
                "district": district,
                "price_hour": Decimal(price_hour) if price_hour else None,
                "price_day": Decimal(price_day) if price_day else None,
                "price_month": Decimal(price_month) if price_month else None,
            },
        )
        missing = photo_count - listing.photos.count()
        for i in range(missing):
            self._attach_photo(listing, seed_id=listing.id * 10 + i)
        return listing

    def _attach_photo(self, listing, seed_id):
        try:
            url = f"https://picsum.photos/seed/ijara-{seed_id}/800/600"
            with urllib.request.urlopen(url, timeout=6) as response:
                raw = response.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            raw = self._placeholder_jpeg(listing.title)

        order = listing.photos.count()
        photo = ListingPhoto(listing=listing, sort_order=order)
        photo.image.save(f"seed-{listing.id}-{order}.jpg", ContentFile(raw), save=True)

    def _placeholder_jpeg(self, text):
        image = Image.new("RGB", (800, 600), color=(70, 100, 140))
        draw = ImageDraw.Draw(image)
        draw.text((40, 280), text[:30], fill=(255, 255, 255))
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    def _make_bookings(self, listings, users):
        """Drive each demo booking through the FSM so audit rows exist."""
        Booking.objects.filter(renter__email__endswith="@ijara.demo").delete()

        now = timezone.now().replace(minute=0, second=0, microsecond=0)

        # (listing_idx, renter_idx, start_offset_days, end_offset_days,
        #  target_state, payment_method)
        # Past windows for completed/cancelled, near-future for live demo.
        plan = [
            (0, 1, 7, 10, BookingState.REQUESTED.value, "cash"),
            (3, 2, 14, 17, BookingState.ACCEPTED.value, "cash"),
            (4, 1, 21, 22, BookingState.PAID.value, "stripe"),
            (9, 2, 30, 33, BookingState.PICKED_UP.value, "cash"),
            (13, 3, 40, 41, BookingState.RETURNED.value, "cash"),
            (15, 0, -30, -27, BookingState.COMPLETED.value, "cash"),
            (5, 2, -20, -15, BookingState.CANCELLED.value, "cash"),
            (7, 3, 50, 52, BookingState.REJECTED.value, "cash"),
        ]

        for listing_idx, renter_idx, start_offset, end_offset, target, payment in plan:
            listing = listings[listing_idx]
            renter = users[renter_idx]
            if renter.id == listing.owner_id:
                renter = users[(renter_idx + 1) % len(users)]
            owner = listing.owner

            start_at = now + timedelta(days=start_offset)
            end_at = now + timedelta(days=end_offset)
            unit, unit_price, quantity, total = calculate_booking_price(listing, start_at, end_at)

            # Insert directly so seeded past-dated bookings (completed /
            # cancelled) are not blocked by the "no start in the past"
            # rule create_booking enforces for real users.
            with db_transaction.atomic():
                booking = Booking.objects.create(
                    listing=listing,
                    renter=renter,
                    start_at=start_at,
                    end_at=end_at,
                    state=BookingState.REQUESTED.value,
                    payment_method=payment,
                    unit=unit,
                    unit_price=unit_price,
                    quantity=quantity,
                    total_amount=total,
                    note=f"Seeded demo booking targeting {target}.",
                )
                BookingStateTransition.objects.create(
                    booking=booking,
                    from_state="",
                    to_state=BookingState.REQUESTED.value,
                    actor=renter,
                    reason="seeded demo",
                )

            for to_state, role in self._fsm_path(target):
                actor = owner if role == "owner" else renter if role == "renter" else None
                transition(booking, to_state, actor=actor, reason="seeded demo")

    def _fsm_path(self, target):
        """Sequence of (state, actor_role) calls to reach target from REQUESTED."""
        if target == BookingState.REQUESTED.value:
            return []
        if target == BookingState.REJECTED.value:
            return [(BookingState.REJECTED.value, "owner")]
        if target == BookingState.CANCELLED.value:
            return [(BookingState.CANCELLED.value, "renter")]
        if target == BookingState.ACCEPTED.value:
            return [(BookingState.ACCEPTED.value, "owner")]
        if target == BookingState.PAID.value:
            return [
                (BookingState.ACCEPTED.value, "owner"),
                (BookingState.PAID.value, "system"),
            ]
        if target == BookingState.PICKED_UP.value:
            return [
                (BookingState.ACCEPTED.value, "owner"),
                (BookingState.PICKED_UP.value, "owner"),
            ]
        if target == BookingState.RETURNED.value:
            return [
                (BookingState.ACCEPTED.value, "owner"),
                (BookingState.PICKED_UP.value, "owner"),
                (BookingState.RETURNED.value, "owner"),
            ]
        if target == BookingState.COMPLETED.value:
            return [
                (BookingState.ACCEPTED.value, "owner"),
                (BookingState.PICKED_UP.value, "owner"),
                (BookingState.RETURNED.value, "owner"),
                (BookingState.COMPLETED.value, "owner"),
            ]
        return []
