from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Brand, Base, Model, Manager

engine = create_engine('sqlite:///carmodel.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy Manager 1
Manager1 = Manager(name="Roberto Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(Manager1)
session.commit()

# Manager 1 Brand
brand1 = Brand(manager_id=1, name="BMW")
session.add(brand1)
session.commit()

# Add Model To The Brand
model1 = Model(name="8 Series Coupe",
               description='''Pulse-racing acceleration made to measure: the
               new BMW 8 Series Coupe combines the character of a sports car
               with the spirit of the BMW luxury class, creating a new form of
               aesthetics.''',
               price="$25000", brand_id=brand1.id)
session.add(model1)
session.commit()

model2 = Model(name="X5 Series",
               description='''The boss is here and puts everyone in their
               place: the new BMW X5. Its presence is written all over its
               face principled, powerful and elegant. The potent one-piece
               double kidney gives you an idea of what happens when it takes
               a deep breath. And the heightened X design of the headlights
               leaves no doubt about who is in the driving seat.''',
               price="$24000", brand_id=brand1.id)
session.add(model2)
session.commit()

model3 = Model(name="3 Series Sedan", description='''The original since 1975:
               The BMW 3 Series is the epitome of the sporty sedan. In its
               sixth generation, this irresistible combination of dynamic
               design, unrivalled agility and intelligent ConnectedDrive
               features is as impressive as ever.''',
               price="$250000", brand_id=brand1.id)
session.add(model3)
session.commit()

print "added menu items!"
